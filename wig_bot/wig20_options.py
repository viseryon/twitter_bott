import pandas as pd
import requests
import yfinance as yf
from datetime import datetime as dt, timedelta
from matplotlib import pyplot as plt
plt.style.use('dark_background')


def get_options():

    td = dt.today()

    r = requests.get(
        'https://www.gpw.pl/ajaxindex.php?action=DRGreek&start=list&format=html&lang=PL')
    date, df = pd.read_html(r.text, encoding='utf-8')

    df.set_index('Lp', inplace=True)
    df.columns = ['title', 'imp_vol', 'vol', 'rfr',
                  'div_y', 'delta', 'gamma', 'theta', 'vega', 'rho']
    df.iloc[:, 3:] /= 10_000
    df.iloc[:, 1:3] /= 100

    expirations = list(pd.date_range(
        td.strftime(r'%Y-%m-%d'),
        dt(td.year + 1, 12, 31).strftime(r'%Y-%m-%d'),
        freq='WOM-3FRI'))
    expirations = [str(x).split()[0] for x in expirations]
    expirations = expirations[:12]

    expirations
    exps = dict()
    for exp in expirations:
        exps[int(exp[5:7])] = exp

    options = {}
    for i in range(24):
        kod = chr(i + 65)
        typ, i = divmod(i, 12)
        msc = i + 1

        options[kod] = {'date': msc, 'cp': bool(1 - typ)}

    for kod in options:
        options[kod]['date'] = exps[options[kod]['date']]

    exp_date, c_p, strike = [], [], []
    for i, w in df.iterrows():
        exp_date.append(options[w['title'][4]]['date'])
        c_p.append(options[w['title'][4]]['cp'])
        strike.append(int(w['title'][-4:]))

    # options = dict()
    # for i, exp in zip(range(65, 89), 2 * expirations):
    #     if i - 65 < 12:
    #         options[chr(i)] = [True, exp]
    #     else:
    #         options[chr(i)] = [False, exp]

    # exp_date, c_p, strike = [], [], []
    # for i, w in df.iterrows():
    #     exp_date.append(options[w['title'][4]][1])
    #     c_p.append(options[w['title'][4]][0])
    #     strike.append(int(w['title'][-4:]))

    df['exp_date'] = exp_date
    df['c_p'] = c_p
    df['strike'] = strike

    date = date.values.flatten()[0]
    date = date.split(' | ')[1]
    date = dt.strptime(date, r'%Y-%m-%d').date()

    return df, expirations, date


def get_todays_options_quotes(full: bool = False) -> pd.DataFrame:

    opcje, exps, td = get_options()
    if td != dt.today().date():
        print('wig20_options.get_today_option_quotes: rozne daty')
        return False

    df = pd.read_html('https://www.bankier.pl/gielda/notowania/opcje')
    df = df[0].dropna()
    df.columns = ['title', 'kurs', 'zmiana_abs', 'zmiana_pct',
                  'otwarcie', 'maxx', 'minn', 'czas', 'exp_date']

    df[['maxx', 'minn', 'otwarcie']] /= 10_000

    df['kurs'] /= 100

    df['zmiana_pct'] = df['zmiana_pct'].str.replace(',', '.')
    df['zmiana_pct'] = df['zmiana_pct'].str.rstrip('%')
    df['zmiana_pct'] = df['zmiana_pct'].astype(float)

    full_df = pd.merge(opcje, df, on='title', how='outer')
    full_df.rename({'exp_date_x': 'exp_date'}, axis=1, inplace=True)
    full_df.drop(columns='exp_date_y', inplace=True)

    if not full:
        return full_df.dropna()
    else:
        return full_df


def get_wig20():

    noww = dt.now().strftime(r'%Y-%m-%d')
    wig20 = yf.download('WIG20.WA', noww, period='1d')
    wig20 = wig20['Adj Close'][0]

    # df = pd.read_html('https://gpwbenchmark.pl/ajaxindex.php?action=GPWIndexes&start=showTable&tab=indexes&lang=PL')
    # df = df[0]
    # cena = df.iloc[0][8]
    # cena = cena.replace(u'\xa0', '').replace(',', '.')
    # wig20 = float(cena)

    return round(wig20, 2)


def do_charts():

    noww = dt.now()
    td = dt.date(noww)

    noww = noww.strftime(r'%Y/%m/%d %H:%M:%S')

    chain, exp_dates, date = get_options()
    if date != td:
        print('wig20_options.do_charts: rozne daty')
        return False

    wig20 = get_wig20()

    avb_dates = []

    def main_plot():

        fig, ax = plt.subplots()

        for i, date in enumerate(exp_dates):

            period_options = chain[chain.exp_date == date]

            if period_options.shape[0]:
                avb_dates.append(date)

                data = period_options.groupby('strike').mean(
                    numeric_only=True).delta + 0.5

                plt.plot(data, label=date)

        plt.tight_layout(pad=3, h_pad=4)
        plt.axvline(x=wig20, label='curr wig20',
                    ymin=0.1, ymax=0.9, ls='dashed')
        fig.text(0.1, 0.02, noww)
        fig.text(0.4, 0.02, '@SliwinskiAlan')
        fig.text(0.75, 0.02, 'source: www.gpw.pl')
        plt.ylabel('probability')
        plt.xlabel('strike')
        plt.grid(which='both', alpha=0.5)
        plt.title(f'Price target of WIG20 based on option contracts')
        plt.legend()
        fig.savefig('all.png', transparent=False)

        return ax

    def simple_plots():

        r = list()

        for date in avb_dates:
            period_options = chain[chain.exp_date == date]
            data = period_options.groupby('strike').mean(
                numeric_only=True).delta + 0.5

            fig, ax = plt.subplots()
            # f = plt.subplots()

            plt.plot(data, label=date)
            plt.tight_layout(pad=3, h_pad=4)
            plt.axvline(x=wig20, label='curr wig20',
                        ymin=0.1, ymax=0.9, ls='dashed')
            fig.text(0.1, 0.02, noww)
            fig.text(0.4, 0.02, '@SliwinskiAlan')
            fig.text(0.75, 0.02, 'source: www.gpw.pl')
            plt.ylabel('probability')
            plt.xlabel('strike')
            plt.grid(which='both', alpha=0.5)
            plt.title(
                f'Price target of WIG20 based on {date} option contracts')
            plt.legend()
            fig.savefig(f'{date}.png', transparent=False)

            r.append(ax)

        return r

    def both():
        r = [main_plot()]
        r.extend(simple_plots())
        return r

    return both()


if __name__ == '__main__':
    wig = get_wig20()
    print(wig)
