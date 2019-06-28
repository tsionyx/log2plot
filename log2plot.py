#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import argparse
import datetime
import logging
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import pytz

LOG = logging.getLogger(__file__ if __name__ == '__main__' else __name__)


def parse_date(dt, to_utc=True):
    """
    Parse date, returned from POSIX ``date`` command.
    e.g. 'Wed Mar  3 20:38:49 +08 2010'
    """
    LOG.debug('Parsing date string %s ...', dt)
    parts = dt.split()
    fmt = '%a %b %d %H:%M:%S %z %Y'

    if len(parts) == 6:  # [Dow, Mth, D, HH:MM:SS, TZ, YYYY]
        tz = parts[4]
        if tz[0] in ('+', '-') and len(tz) == 3:
            parts[4] = tz + '00'

            dt = ' '.join(parts)

    dt = datetime.datetime.strptime(dt, fmt)
    if to_utc:
        dt = dt.astimezone(pytz.utc)

    return dt


def _try_parse_date(dt, to_utc=True):
    try:
        return parse_date(dt, to_utc=to_utc)
    except ValueError:
        return None


def parse_time_series(stream):
    dt = None

    line_no = 0
    while True:
        line = stream.readline()
        if not line:
            break

        line_no += 1

        line = line.strip()
        if not line:  # empty line
            continue

        try:
            if dt is None:
                dt = _try_parse_date(line)
                if not dt:
                    LOG.warning('Line %s: %s cannot be parsed to date and will be skipped.',
                                line_no, line)
            else:
                try:
                    value = float(line)
                except ValueError:
                    another_dt = _try_parse_date(line)
                    if not another_dt:
                        raise

                    LOG.warning('Timestamp %s has invalid associated value, '
                                'skipping to the next line (%s)', dt, line_no)
                    dt = another_dt
                else:
                    yield (dt, value)
                    dt = None

        except (TypeError, ValueError):
            LOG.error('Error on the line %s', line_no)
            raise


def data_frame(time_series, value_column_name, drop_duplicates=True):
    df = pd.DataFrame(time_series, columns=['date', value_column_name])
    df = df.set_index('date').sort_index()
    if drop_duplicates:
        df = df.groupby(df.index).mean()
    return df


def do_plot(df, date_format='%d/%m/%Y %H:%M', save_to=None):
    # plot = df.plot()
    # fig = plot.get_figure()

    fig, ax = plt.subplots()

    xfmt = mdates.DateFormatter(date_format)
    ax.xaxis.set_major_formatter(xfmt)

    plt.xticks(rotation=90)
    ax.plot(df)
    ax.legend(df.columns, loc='upper left')

    if save_to:
        # do not crop the bottom edge
        fig.savefig(save_to, bbox_inches='tight')


def main():
    parser = argparse.ArgumentParser(description='Plot bash-generated time series')
    parser.add_argument('--input', help='If no file specified, the standard input will be used')
    parser.add_argument('-o', '--output', default='out.png', help='Path to image to save plot to')
    parser.add_argument('--metric', default='value', help='Name of the metric')
    parser.add_argument('--save-csv', action='store_true',
                        help='Save the dataframe in the CSV file for further analyzing')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Provide statistic info about the data')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    if args.input:
        f = open(args.input)
    else:
        f = sys.stdin

    df = data_frame(parse_time_series(f), args.metric)
    if args.save_csv:
        df.to_csv(args.metric + '.csv')

    if args.verbose:
        print(df.describe(), file=sys.stderr)

    do_plot(df, save_to=args.output)


if __name__ == '__main__':
    main()
