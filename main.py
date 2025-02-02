"""Script running my twitter bot.

Script includes TwitterBot class that will run bot that posts pictures with WIG returns.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from http.client import IncompleteRead
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import pytz
import yahooquery as yq
import yfinance as yf
from pandas import Index
from tweepy import API, Client, OAuth1UserHandler

import keys

os.chdir(Path(__file__).parent)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(),
    ],
)


class TwitterBot:
    """Class that runs the twitter bot.

    Attributes:
        client (Client): tweepy client
        api (API): tweepy api
        wig_components (pd.DataFrame): components of WIG index
        tickers (list): tickers of WIG components
        prices (pd.DataFrame): prices of WIG components
        wig (pd.Series): prices of WIG index
        curr_prices (pd.Series): current prices of WIG components
        ts (pd.DataFrame): time series of date data
        tzinfo (pytz.timezone): timezone
        today (pd.Timestamp): today's date

    """

    def __init__(self) -> None:
        """Init method.

        Autheticates with tweepy, downloads WIG components, prices and WIG index.
        """
        client, api = self.auth()
        self.client: Client = client
        self.api: API = api
        logging.info("auth complete")

        self.tzinfo = pytz.timezone("Europe/Warsaw")
        self.today = pd.Timestamp(datetime.now(tz=self.tzinfo).today())

        wig_components = self._get_wig_components()
        self.wig_components: pd.DataFrame = wig_components
        self.tickers: list = wig_components.yf_ticker.to_list()
        logging.info("downloaded wig components")

        self.prices, self.wig = self._get_data()
        self.curr_prices = self.prices.iloc[-1]
        logging.info("downloaded data")

        ts = pd.DataFrame(self.prices.index)
        ts["year"] = ts.Date.dt.year
        ts["quarter"] = ts.Date.dt.quarter
        ts["month"] = ts.Date.dt.month
        ts["week"] = ts.Date.dt.isocalendar().week
        ts["day"] = ts.Date.dt.day
        ts["weekday"] = ts.Date.dt.weekday
        self.ts: pd.DataFrame = ts

        logging.info("init complete")

    def auth(self) -> tuple[Client, API]:
        """Auth method.

        Reads from keys all the necessary secrets and performs auth with tweepy.

        Returns:
            tuple[Client, API]: stuff needed make tweets

        """
        logging.info("authenicating...")
        bearer_token = keys.BEARER_TOKEN
        api_key = keys.API_KEY
        access_token = keys.ACCESS_TOKEN
        access_token_secret = keys.ACCESS_TOKEN_SECRET
        api_secret = keys.API_SECRET

        try:
            # https://stackoverflow.com/questions/48117126/when-using-tweepy-cursor-what-is-the-best-practice-for-catching-over-capacity-e
            client = Client(bearer_token, api_key, api_secret, access_token, access_token_secret)
            auth = OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
            api = API(auth, retry_count=5, retry_delay=5, retry_errors={503})
        except Exception:
            logging.exception("auth failed")
            sys.exit(1)

        return client, api

    def make_tweet(self, text: str, pictures: list[str]) -> None:
        """Make a tweet.

        Args:
            text (str): text to put in the tweet
            pictures (list[str]): list of paths to pictures to tweet

        """
        if pictures:
            lst = []
            for picture in pictures:
                media = self.api.media_upload(filename=picture)
                lst.append(media.media_id_string)

            self.client.create_tweet(text=text, media_ids=lst)

            for picture in pictures:
                Path(picture).unlink()

        else:
            self.client.create_tweet(text=text)

    def _get_data(self) -> tuple[pd.DataFrame, pd.Series]:
        """Get data from YahooFinance.

        Get pd.DataFrame of prices of selected tickers and transform it.

        Returns:
            pd.DataFrame: prices with index of dates and columns of stock prices

        """
        tickers = yf.Tickers([*self.tickers, "WIG.WA"])

        # request more than one year
        # to ensure there will be at least one datapoint from the previous year
        start_date = datetime.now(tz=self.tzinfo).today() - timedelta(days=400)

        prices: pd.DataFrame = tickers.history(
            start=start_date,
            timeout=20,
            progress=False,
            threads=False,
            auto_adjust=False,
        ).Close
        prices.columns = [tick.removesuffix(".WA") for tick in prices.columns]
        prices = prices.ffill()

        # after using ffill to fill values when there was no price change
        # during the trading session
        # bfill fills values before the first occurance
        # this provide an anchor value to calculate longer period
        prices = prices.bfill()

        wig = prices.WIG
        prices = prices.drop(columns=["WIG"])

        return prices, wig

    @staticmethod
    def get_symbol(
        query: str,
        preferred_exchange: str = "WSE",
        max_tries: int = 5,
        tries: int = 0,
    ) -> str:
        """Get ticker.

        Searches Yahoo Finance for a ticker by other identifier.

        Args:
            query (str): some identifier
            preferred_exchange (str, optional): what exchange to prioritize. Defaults to "WSE".
            max_tries (int, optional): how many times to try to get the ticker. Defaults to 5.
            tries (int, optional): current try. Defaults to 0.

        Returns:
            _type_: _description_

        """
        try:
            data = yq.search(query)
        except ValueError as e:  # Will catch JSONDecodeError
            if tries >= max_tries:
                msg = f"YahooFinance have not returned the necessary ticker\n{query = }"
                raise ValueError(msg) from e
            return TwitterBot.get_symbol(query, tries=tries + 1)
        else:
            quotes = data["quotes"]
            if len(quotes) == 0:
                if tries >= max_tries:
                    msg = f"YahooFinance have not returned the necessary ticker\n{query = }"
                    raise ValueError(msg)
                return TwitterBot.get_symbol(query, tries=tries + 1)

            symbol = quotes[0]["symbol"]
            for quote in quotes:
                if quote["exchange"] == preferred_exchange:
                    symbol: str = quote["symbol"]
                    break
            return symbol

    def _get_wig_components(self, retry: int = 20) -> pd.DataFrame:
        # get data from source
        tries = 0
        while tries < retry:
            try:
                updated_components = pd.read_html(
                    "https://gpwbenchmark.pl/ajaxindex.php?action=GPWIndexes&start=ajaxPortfolio&format=html&lang=EN&isin=PL9999999995&cmng_id=1011",
                )[0]
            except IncompleteRead:
                tries += 1
            else:  # if downloading data worked
                break
        else:  # downloading data failed every time
            err = f"downloading wig components failed {retry} times"
            logging.error(err)
            sys.exit(1)

        updated_components = updated_components.iloc[:, :3]
        updated_components.columns = ["company", "ISIN", "shares_num"]

        saved_components = pd.read_csv("wig_comps.csv")

        # add tickers to the source data
        full_components = saved_components.merge(
            updated_components,
            how="right",
            on=["company", "ISIN"],
        )

        pretty_industry = {
            "Financial Data & Stock Exchanges": "Financial Data<br>& Stock Exchanges",
            "Utilities - Regulated Gas": "Regulated Gas",
            "Utilities - Independent Power Producers": "Independent<br>Power Producers",
            "Utilities - Renewable": "Renewable",
            "Utilities - Regulated Electric": "Regulated Electric",
            "Real Estate - Diversified": "Diversified",
            "Real Estate Services": "Services",
            "Real Estate - Development": "Development",
            "Farm & Heavy Construction Machinery": "Farm & Heavy<br>Construction Machinery",
            "Staffing & Employment Services": "Staffing & Employment<br>Services",
            "Tools & Accessories": "Tools & Accessories",
            "Building Products & Equipment": "Building Products & Equipment",
            "Integrated Freight & Logistics": "Integrated Freight & Logistics",
            "Specialty Industrial Machinery": "Specialty Industrial<br>Machinery",
            "Electrical Equipment & Parts": "Electrical Equipment & Parts",
            "Metal Fabrication": "Metal Fabrication",
            "Aerospace & Defense": "Aerospace & Defense",
            "Paper & Paper Products": "Paper & Paper Products",
            "Specialty Chemicals": "Specialty Chemicals",
            "Specialty Business Services": "Specialty Business<br>Services",
            "Drug Manufacturers - Specialty & Generic": "Drug Manufacturers<br>Specialty & Generic",
            "Medical Care Facilities": "Medical Care<br>Facilities",
            "Medical Instruments & Supplies": "Medical Instruments<br>& Supplies",
            "Pharmaceutical Retailers": "Pharmaceutical<br>Retailers",
            "Electronic Components": "Electronic Components",
            "Scientific & Technical Instruments": "Scientific & Technical<br>Instruments",
            "Electronics & Computer Distribution": "Electronics & Computer<br>Distribution",
            "Furnishings, Fixtures & Appliances": "Furnishings,<br>Fixtures & Appliances",
            "Travel Services": "Travel Services",
            "Information Technology Services": "Information Technology<br>Services",
            "Software - Infrastructure": "Infrastructure",
            "Medical Devices": "Medical Devices",
            "Banks - Regional": "Banks - Regional",
            "Oil & Gas Integrated": "Integrated",
            "Insurance - Property & Casualty": "Property & Casualty",
            "Internet Retail": "Internet Retail",
            "Apparel Manufacturing": "Apparel Manufacturing",
            "Copper": "Copper",
            "Grocery Stores": "Grocery Stores",
            "Electronic Gaming & Multimedia": "Electronic<br>Gaming & Multimedia",
            "Engineering & Construction": "Engineering & Construction",
            "Aluminum": "Aluminum",
            "Credit Services": "Credit Services",
            "Banks - Diversified": "Banks - Diversified",
            "Apparel Retail": "Apparel Retail",
            "Leisure": "Leisure",
            "Telecom Services": "Telecom Services",
            "Auto Parts": "Auto Parts",
            "Capital Markets": "Capital Markets",
            "Software - Application": "Application",
            "Discount Stores": "Discount Stores",
            "Entertainment": "Entertainment",
            "Coking Coal": "Coking Coal",
            "Medical Distribution": "Medical Distribution",
            "Restaurants": "Restaurants",
            "Agricultural Inputs": "Agricultural Inputs",
            "Diagnostics & Research": "Diagnostics & Research",
            "Waste Management": "Waste Management",
            "Biotechnology": "Biotechnology",
            "Oil & Gas Refining & Marketing": "Refining & Marketing",
            "Railroads": "Railroads",
            "Airlines": "Airlines",
            "Residential Construction": "Residential<br>Construction",
            "Publishing": "Publishing",
            "Steel": "Steel",
            "Thermal Coal": "Thermal Coal",
            "Confectioners": "Confectioners",
            "Packaged Foods": "Packaged Foods",
            "Specialty Retail": "Specialty Retail",
            "Chemicals": "Chemicals",
            "Beverages - Wineries & Distilleries": "Wineries & Distilleries",
            "Asset Management": "Asset Management",
            "Infrastructure Operations": "Infrastructure<br>Operations",
            "Conglomerates": "Conglomerates",
            "Farm Products": "Farm Products",
            "Security & Protection Services": "Security & Protection<br>Services",
            "Solar": "Solar",
            "Computer Hardware": "Computer Hardware",
            "Broadcasting": "Broadcasting",
            "Rental & Leasing Services": "Rental & Leasing<br>Services",
            "Industrial Distribution": "Industrial<br>Distribution",
            "Advertising Agencies": "Advertising<br>Agencies",
            "Household & Personal Products": "Household & Personal<br>Products",
            "Building Materials": "Building Materials",
            "Food Distribution": "Food Distribution",
            "Trucking": "Trucking",
            "Beverages - Non-Alcoholic": "Non-Alcoholic",
            "Footwear & Accessories": "Footwear & Accessories",
            "Consulting Services": "Consulting Services",
            "Communication Equipment": "Communication<br>Equipment",
            "Internet Content & Information": "Internet<br>Content & Information",
            "Lumber & Wood Production": "Lumber & Wood<br>Production",
            "Insurance - Diversified": "Diversified",
        }
        # check for empty data
        empty_data = full_components[full_components.isna().any(axis=1)]
        if empty_data.empty:
            full_components["ticker"] = full_components["yf_ticker"].str.removesuffix(".WA")
            full_components.industry = full_components.industry.replace(pretty_industry)
            return full_components
        # get new ticker from Yahoo Finance
        for indx, (
            company,
            isin,
            yf_ticker,
            sector,
            industry,
            _,
        ) in empty_data.iterrows():
            warn = f"Company {company} had missing data."
            logging.warning(warn)

            if pd.isna(yf_ticker):
                ticker = self.get_symbol(isin)
                # add missing ticker
                full_components.loc[indx, "yf_ticker"] = ticker  # type: ignore
            else:
                ticker = yf_ticker

            if pd.isna(sector) or pd.isna(industry):
                # add missing sector and industry values
                asset_profile = yq.Ticker(ticker).asset_profile[ticker]

                # check for correct data returned
                # new companies may have no sector/industry data
                if not isinstance(asset_profile, dict):
                    full_components.loc[indx, "sector"] = None  # type: ignore
                    full_components.loc[indx, "industry"] = None  # type: ignore
                else:
                    full_components.loc[indx, "sector"] = asset_profile["sector"]  # type: ignore
                    full_components.loc[indx, "industry"] = asset_profile["industry"]  # type: ignore

        # save new csv with full WIG
        full_components.drop(columns="shares_num").to_csv("wig_comps.csv", index=False)

        full_components.industry = full_components.industry.replace(pretty_industry)
        full_components["ticker"] = full_components["yf_ticker"].str.removesuffix(".WA")
        return full_components

    def get_periods_indicies(self, period: str = "1D") -> Index:
        """Get a start date and last date of some period to calculate returns.

        possible periods: YTD, QTD, MTD, 1W, 1D, 1Y

        Args:
            period (str, optional): what period the changes will be calculated. Defaults to "1D".

        Raises:
            NotImplementedError

        Returns:
            Index: index to use with df.iloc

        """
        if period == "YTD":
            return (
                self.ts.loc[self.ts[self.ts.year == self.today.year - 1].index.max() :]
                .iloc[[0, -1]]
                .index
            )
        if period == "MTD":
            return (
                self.ts.iloc[
                    self.ts[
                        (self.ts.year == self.today.year) & (self.ts.month == self.today.month)
                    ].index.min()
                    - 1 :
                ]
                .iloc[[0, -1]]
                .index
            )
        if period == "QTD":
            return (
                self.ts.iloc[
                    self.ts[
                        (self.ts.year == self.today.year) & (self.ts.quarter == self.today.quarter)
                    ].index.min()
                    - 1 :
                ]
                .iloc[[0, -1]]
                .index
            )
        if period == "1W":  # remember to do this on weekends!
            return (
                self.ts.iloc[
                    self.ts[
                        (self.ts.year == self.today.year) & (self.ts.week == self.today.week)
                    ].index.min()
                    - 1 :
                ]
                .iloc[[0, -1]]
                .index
            )
        if period == "1D":
            return self.ts.iloc[[-2, -1]].index
        if period == "1Y":
            return self.ts.iloc[self.ts.index.max() - 252 :].iloc[[0, -1]].index
        msg = f"period {period} not available"
        raise NotImplementedError(msg)

    def is_trading_day(self) -> bool:
        """Check if today was a trading day by looking at dates in downloaded data.

        Returns:
            bool

        """
        return pd.Timestamp(datetime.now(tz=self.tzinfo).date()) in self.ts.Date.to_list()

    def _prepare_tweet_text(self, data: pd.DataFrame, wig_return: float, period: str) -> str:
        """Prepare text for the tweet.

        Method for calculating data that will be on the tweet.

        Args:
            data (pd.DataFrame): data to calculate sectors returns
            wig_return (float): value of WIG index return
            period (str): period to go to the tweet title

        Returns:
            str: text to directly put on the tweet

        """
        data["contribution"] = data.mkt_cap * data.returns

        sectors_return = (
            data.groupby("sector")["contribution"].sum() / data.groupby("sector")["mkt_cap"].sum()
        ).sort_values(ascending=False)

        tweet_text = f"WIG Index {period} performance\n"  #: {wig_return:.2%}"

        # add this when yahoo finance provides wig index data
        # if wig_return > 0.02:
        #     tweet_text += " 🟢🟢🟢\n"
        # elif wig_return > 0.01:
        #     tweet_text += " 🟢🟢\n"
        # elif wig_return > 0.005:
        #     tweet_text += " 🟢\n"
        # elif wig_return > -0.005:
        #     tweet_text += " ➖\n"
        # elif wig_return > -0.01:
        #     tweet_text += " 🔴\n"
        # elif wig_return > -0.02:
        #     tweet_text += " 🔴🔴\n"
        # else:
        # tweet_text += " 🔴🔴🔴\n"

        tweet_text += (
            f"\n🟢 {data.ticker.iloc[0]} {data.company.iloc[0]} {data.returns.iloc[0]:.2%}\n"
            f"🔴 {data.ticker.iloc[-1]} {data.company.iloc[-1]} {data.returns.iloc[-1]:.2%}\n\n"
        )

        max_lines = 3
        for medal, (i, (sector, change)) in zip(
            ("🥇", "🥈", "🥉"),
            enumerate(sectors_return.items(), start=1),
        ):
            if i <= max_lines:
                tweet_text += f"{medal}\t{sector} -> {change:.2%}\n"
            else:
                break

        tweet_text += "\n#WIG #GPW #giełda #inwestycje #akcje"

        return tweet_text

    def _prepare_data_for_heatmap_and_tweet(self, period: str) -> tuple[pd.DataFrame, float]:
        # calculate returns
        indicies = self.get_periods_indicies(period)
        data: pd.DataFrame = self.prices.iloc[indicies].pct_change().T.iloc[:, [-1]]
        try:
            data.columns = ["returns"]
        except ValueError:
            logging.exception(data)
            logging.exception(self.prices)
            sys.exit(1)

        # calculate wig returns
        wig_return: float = self.wig.iloc[indicies].pct_change().values[0]

        data = data.merge(
            self.wig_components.set_index("ticker"),
            right_index=True,
            left_index=True,
            validate="one_to_one",
        )
        # data.columns
        # columns 'company', 'ISIN', 'yf_ticker', 'sector', 'industry', 'shares_num', 'returns'

        data = data.drop(columns=["ISIN", "yf_ticker"])
        data["curr_prices"] = self.curr_prices

        data["mkt_cap"] = data["curr_prices"] * data["shares_num"]
        data["WIG"] = "WIG"
        data = (
            data.reset_index()
            .rename({"index": "ticker"}, axis=1)
            .sort_values("returns", ascending=False)
        )

        # check for nans in dataframe
        if data.isna().any().any():
            logging.error("THERE ARE NULL VALUES IN DATAFRAME WITH PRICES")
            logging.error(data[data.isna().any(axis=1)])

        return data, wig_return

    ### performance heatmaps

    def chart_heatmap(self, data: pd.DataFrame, path: str, period: str) -> None:
        """Save wig heatmap.

        Creates actual wig heatmap and saves it.

        Args:
            data (pd.DataFrame): cols(
                'ticker', 'company', 'sector', 'industry',
                'shares_num', 'returns', 'curr_prices', 'mkt_cap'
            )
            path (str): filename with extension
            period (str): used only for title

        """
        font = "Times New Roman"

        if period == "1W":
            additional_info = f" ⁕ {self.today.week}W{self.today.year}"
        elif period == "MTD":
            additional_info = f" ⁕ {self.today.month}M{self.today.year}"
        elif period == "QTD":
            additional_info = f" ⁕ {self.today.quarter}Q{self.today.year}"
        else:  # 1D, YTD, 1Y
            additional_info = ""

        # colour bounds for different periods
        bounds = {
            "1D": 0.03,
            "1W": 0.1,
            "MTD": 0.2,
            "QTD": 0.3,
            "YTD": 0.5,
            "1Y": 0.5,
        }

        fig = px.treemap(
            data,
            path=["WIG", "sector", "ticker"],
            values="mkt_cap",
            color="returns",
            color_continuous_scale=["#CC0000", "#292929", "#00CC00"],
            custom_data=data[["returns", "company", "ticker", "curr_prices", "sector"]],
        )

        fig.update_traces(
            insidetextfont={"size": 140, "family": font},
            textfont={"size": 60, "family": font},
            textposition="middle center",
            texttemplate="<br>%{customdata[2]}<br>    <b>%{customdata[0]:.2%}</b>     <br><sup><i>%{customdata[3]:.2f} zł</i><br></sup>",  # noqa: E501
            marker={
                "cornerradius": 25,
                "line_width": 3,
                "line_color": "#2e2e2e",
            },
        )

        fig.update_coloraxes(
            showscale=True,
            cmin=-bounds[period],
            cmax=bounds[period],
            cmid=0,
            colorbar={
                "title_text": "",
                "thickness": 175,
                "orientation": "h",
                "y": 1.035,
                "tickfont": {
                    "color": "white",
                    "size": 125,
                    "family": font,
                },
                "ticklabelposition": "inside",
                "tickvals": [-bounds[period] * 0.95, bounds[period] * 0.95],
                "ticktext": [f"{-bounds[period]:.0%}", f"{bounds[period]:.0%}"],
            },
        )

        fig.update_layout(
            margin={"t": 350, "l": 5, "r": 5, "b": 120},
            width=7680,
            height=4320,
            title={
                "text": f"INDEX WIG<br><sup>{period} performance{additional_info} ⁕ {datetime.now(self.tzinfo):%Y/%m/%d}</sup>",  # noqa: E501
                "font": {"color": "white", "size": 170, "family": font},
                "yanchor": "middle",
                "xanchor": "center",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "pad": {"t": 100, "b": 100},
            },
            paper_bgcolor="#1a1a1a",
        )

        fig.add_annotation(
            text=("source: YahooFinance!"),
            x=0.90,
            y=-0.023,
            font={"family": font, "size": 80, "color": "white"},
            opacity=0.7,
            align="left",
        )

        fig.add_annotation(
            text=(datetime.now(self.tzinfo).strftime(r"%Y/%m/%d %H:%M")),
            x=0.1,
            y=-0.025,
            font={"family": font, "size": 80, "color": "white"},
            opacity=0.7,
            align="left",
        )

        fig.add_annotation(
            text=("@SliwinskiAlan"),
            x=0.5,
            y=-0.025,
            font={"family": font, "size": 80, "color": "white"},
            opacity=0.7,
            align="left",
        )

        fig.write_image(path)

    def heatmap_and_tweet_text(self, period: str) -> tuple[str, str]:
        """Calculate necessary data and prepares heatmap and text for the tweet.

        Returns:
            tuple[str, str]: path to picture and tweet text

        """
        data, wig_return = self._prepare_data_for_heatmap_and_tweet(period=period)

        path = f"wig_heatmap_{period}.png"
        self.chart_heatmap(data, path, period)

        # text for the tweet
        tweet_text = self._prepare_tweet_text(data, wig_return, period=period)

        return (path, tweet_text)

    def run(self) -> None:
        """Run twitter bot.

        Make calculations, heatmaps and post them to twitter.
        """
        logging.info("running main function")

        # post daily heatmap
        if self.is_trading_day():
            logging.info("posting daily heatmap")
            path, tweet_string = self.heatmap_and_tweet_text("1D")
            self.make_tweet(tweet_string, [path])
            logging.info("tweeted successfully")
        else:
            logging.info("today was not a trading day")

        saturday_in_week = 5
        # on saturday post 1w performance
        if self.today.weekday() == saturday_in_week:
            logging.info("posting weekly heatmap")
            path, tweet_string = self.heatmap_and_tweet_text("1W")
            self.make_tweet(tweet_string, [path])
            logging.info("tweeted successfully")
        else:
            logging.info("not posting weekly heatmap")

        # on last day of the month post 1m performance
        if self.today.is_month_end:
            logging.info("posting monthly heatmap")
            path, tweet_string = self.heatmap_and_tweet_text("MTD")
            self.make_tweet(tweet_string, [path])
            logging.info("tweeted successfully")
        else:
            logging.info("not posting monthly heatmap")

        # on last day of the quarter post 1q performance
        if self.today.is_quarter_end:
            logging.info("posting quarterly heatmap")
            path, tweet_string = self.heatmap_and_tweet_text("QTD")
            self.make_tweet(tweet_string, [path])
            logging.info("tweeted successfully")
        else:
            logging.info("not posting quarterly heatmap")

        # on last day of the year post 1y performance
        if self.today.is_year_end:
            logging.info("posting yearly heatmap")
            path, tweet_string = self.heatmap_and_tweet_text("YTD")
            self.make_tweet(tweet_string, [path])
            logging.info("tweeted successfully")
        else:
            logging.info("not posting yearly heatmap")

        # choose randomly a day to post ytd performance
        # 24 out of 360, so on average every 15 days
        rng = np.random.default_rng()
        if rng.random() < 24 / 360:
            logging.info("posting ytd heatmap")
            path, tweet_string = self.heatmap_and_tweet_text("YTD")
            self.make_tweet(tweet_string, [path])
            logging.info("tweeted successfully")
        else:
            logging.info("not posting ytd heatmap")


if __name__ == "__main__":
    logging.info("starting...")
    bot = TwitterBot()
    bot.run()
