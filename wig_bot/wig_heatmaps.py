from datetime import datetime as dt
from datetime import timedelta, timezone

import pandas as pd
import plotly.express as px
import yahooquery as yq
from matplotlib import pyplot as plt
from pathlib import Path

plt.style.use("dark_background")

timezone_offset = 2.0  # CET Warsaw
tzinfo = timezone(timedelta(hours=timezone_offset))

def get_path(file_name) -> str:
    """returns a path for a file

    Args:
        file_name (str): just a file name

    Returns:
        str: path of that file
    """
    path = Path(__file__).parent
    file = Path(file_name)
    
    return str(path / file)


def wig20_do_chart():
    try:
        data = pd.read_html(
            "https://www.bankier.pl/inwestowanie/profile/quote.html?symbol=WIG20",
            decimal=",",
            thousands="\xa0",
        )[1]
    except:
        return False

    data["Zmiana procentowa"] = data["Zmiana procentowa"].str.replace(",", ".")
    data["Zmiana procentowa"] = data["Zmiana procentowa"].str.rstrip("%").astype(float)
    data.drop(
        columns=["Zmiana", "Wpływ na indeks", "Udział w obrocie", "Udział w portfelu"],
        inplace=True,
    )
    data.rename({"Zmiana procentowa": "Zmiana_pct"}, axis=1, inplace=True)
    data.Zmiana_pct /= 100

    data["Udzial"] = data.Kurs * data.Pakiet

    data["udzial_zmiana_pct"] = data.Zmiana_pct * data.Udzial

    stat_chng = data.udzial_zmiana_pct.sum() / data.Udzial.sum()

    fig = px.treemap(
        data,
        path=[px.Constant("     "), "Ticker"],
        values="Udzial",
        color="Zmiana_pct",
        color_continuous_scale=["#CC0000", "#353535", "#00CC00"],
        custom_data=data[["Zmiana_pct", "Nazwa", "Ticker", "Kurs"]],
    )

    fig.update_traces(
        insidetextfont=dict(
            size=160,
        ),
        textfont=dict(size=40),
        textposition="middle center",
        texttemplate="<br>%{customdata[2]}<br>    <b>%{customdata[0]:.2%}</b>     <br><sup><i>%{customdata[3]:.2f} zł</i><br></sup>",
        marker_line_width=3,
        marker_line_color="#1a1a1a",
        root=dict(color="#1a1a1a"),
    )

    fig.update_coloraxes(
        showscale=True,
        cmin=-0.03,
        cmax=0.03,
        cmid=0,
    )

    fig.update_layout(
        margin=dict(t=200, l=5, r=5, b=120),
        width=7680,
        height=4320,
        title=dict(
            text=f"INDEX WIG20 ⁕ {stat_chng:.2%} ⁕ {dt.now(tzinfo):%Y/%m/%d}",
            font=dict(
                color="white",
                size=150,
            ),
            yanchor="middle",
            xanchor="center",
            xref="paper",
            yref="paper",
            x=0.5,
        ),
        paper_bgcolor="#1a1a1a",
        # paper_bgcolor="rgba(0,0,0,0)",
        colorway=["#D9202E", "#AC1B26", "#7F151D", "#3B6323", "#518A30", "#66B13C"],
    )

    fig.add_annotation(
        text=("source: bankier.com"),
        x=0.90,
        y=-0.023,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=(dt.now(tzinfo).strftime(r"%Y/%m/%d %H:%M")),
        x=0.1,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=("@SliwinskiAlan"),
        x=0.5,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    # fig.show()
    fig.write_image("wig20_heatmap.png")
    return True


def wig_sectors_do_chart():
    l = [
        "BANKI",
        "BUDOW",
        "CHEMIA",
        "NRCHOM",
        "ENERG",
        "INFO",
        "MEDIA",
        "PALIWA",
        "SPOZYW",
        "GORNIC",
        "LEKI",
        "MOTO",
        "ODZIEZ",
        "GRY",
    ]

    lst = [f"WIG-{to}" for to in l]

    data = pd.DataFrame()
    try:
        for sector in lst:
            df = pd.read_html(
                f"https://www.bankier.pl/inwestowanie/profile/quote.html?symbol={sector}",
                decimal=",",
                thousands="\xa0",
            )[1]
            df["Sector"] = [sector] * df.shape[0]
            data = pd.concat([data, df])
    except:
        return False

    data["Zmiana procentowa"] = data["Zmiana procentowa"].str.replace(",", ".")
    data["Zmiana procentowa"] = data["Zmiana procentowa"].str.rstrip("%").astype(float)
    data["Udział w portfelu"] = data["Udział w portfelu"].str.replace(",", ".")
    data["Udział w portfelu"] = data["Udział w portfelu"].str.rstrip("%").astype(float)
    data.drop(columns=["Zmiana", "Wpływ na indeks", "Udział w obrocie"], inplace=True)
    data.rename(
        {"Zmiana procentowa": "Zmiana_pct", "Udział w portfelu": "Udzial"},
        axis=1,
        inplace=True,
    )
    data.Zmiana_pct /= 100
    data.Udzial /= 100

    data["pakiet_pln"] = data.Pakiet * data.Kurs

    data["pakiet_zmiana"] = data.pakiet_pln * data.Zmiana_pct
    data = data.groupby(["Sector"])[["pakiet_zmiana", "pakiet_pln"]].sum(
        numeric_only=True
    )

    data.reset_index(inplace=True)
    data.pakiet_zmiana = data.pakiet_zmiana / data.pakiet_pln

    fig = px.treemap(
        data,
        path=[px.Constant("- - - I N D E K S Y - - -"), "Sector"],
        values="pakiet_pln",
        color="pakiet_zmiana",
        color_continuous_scale=["#CC0000", "#353535", "#00CC00"],
        custom_data=data[["Sector", "pakiet_zmiana"]],
    )

    fig.update_traces(
        insidetextfont=dict(
            size=200,
        ),
        textfont=dict(size=40),
        textposition="middle center",
        texttemplate="<br>      %{customdata[0]}      <br><b>      %{customdata[1]:.2%}      </b>",
        marker_line_width=3,
        marker_line_color="#1a1a1a",
        root=dict(color="#1a1a1a"),
    )

    fig.update_coloraxes(showscale=True, cmin=-0.03, cmax=0.03, cmid=0)

    fig.update_layout(
        margin=dict(t=200, l=5, r=5, b=120),
        width=7680,
        height=4320,
        title=dict(
            text=f"INDEKSY SEKTOROWE WIG ⁕ {dt.now(tzinfo):%Y/%m/%d}",
            font=dict(
                color="white",
                size=150,
            ),
            yanchor="middle",
            xanchor="center",
            xref="paper",
            yref="paper",
            x=0.5,
        ),
        paper_bgcolor="#1a1a1a",
        colorway=["#D9202E", "#AC1B26", "#7F151D", "#3B6323", "#518A30", "#66B13C"],
        coloraxis_colorbar=dict(
            title="",
            thicknessmode="pixels",
            thickness=130,
            tickvals=[-0.029, -0.02, -0.01, 0, 0.01, 0.02, 0.029],
            ticktext=["-3%", "-2%", "-1%", "0%", "+1%", "+2%", "+3%"],
            orientation="v",
            tickfont=dict(
                color="white",
                size=55,
            ),
            ticklabelposition="inside",
        ),
    )

    fig.add_annotation(
        text=("source: bankier.com"),
        x=0.90,
        y=-0.023,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=(dt.now(tzinfo).strftime(r"%Y/%m/%d %H:%M")),
        x=0.1,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=("@SliwinskiAlan"),
        x=0.5,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    # fig.show()
    fig.write_image("wig_sectors_heatmap.png")

    data = data.sort_values("pakiet_zmiana", ascending=False, ignore_index=True)

    data_string = ""
    for indx, (sector, change, _) in data.iterrows():
        sector = sector.removeprefix("WIG-")

        if change > 0.0025:
            data_string += f"{indx + 1}. 🟢"
        elif change > -0.0025:
            data_string += f"{indx + 1}. ➖"
        else:
            data_string += f"{indx + 1}. 🔴"

        data_string += f" {sector:<6} -> {change:6.2%}\n"

        if indx == 5:
            break

    return data_string


def wig_sectors_do_chart_1w_perf():
    today = dt.today()
    week_nr = today.isocalendar().week

    path = get_path('sectors.csv')
    df = pd.read_csv(path)
    df.Ticker = df.Ticker + ".WA"

    prices = yq.Ticker(df.Ticker).history(period="1mo")[["adjclose"]].reset_index()

    prices = prices.pivot(columns="symbol", index="date").droplevel(level=0, axis=1)

    prices_chng = prices.reset_index()
    prices_chng.date = pd.to_datetime(prices_chng.date)
    prices_chng["week_nr"] = prices_chng.date.dt.isocalendar().week
    b = prices_chng[prices_chng.week_nr == week_nr]
    a = prices_chng[
        (prices_chng.week_nr == 52) | (prices_chng.week_nr == week_nr - 1)
    ].tail(1)
    prices_chng = pd.concat([a, b])

    start, end = prices_chng.date.iloc[1], prices_chng.date.iloc[-1]

    prices_chng = prices_chng.drop(columns=["date", "week_nr"])

    prices_chng = (prices_chng.pct_change() + 1).cumprod() - 1

    prices_chng = prices_chng.tail(1).T.reset_index()
    prices_chng.columns = ["Ticker", "Zmiana_pct"]

    kurs = prices.tail(1).T.reset_index()
    kurs.columns = ["Ticker", "Kurs"]

    full = pd.merge(df, prices_chng, on="Ticker")
    data = pd.merge(full, kurs, on="Ticker")

    data["Udzial"] = data.Kurs * data.Pakiet

    data["udzial_zmiana_pct"] = data.Zmiana_pct * data.Udzial

    data = data.groupby(["Sector"])[["udzial_zmiana_pct", "Udzial"]].sum(
        numeric_only=True
    )

    data.reset_index(inplace=True)

    data["Zmiana_pct"] = data.udzial_zmiana_pct / data.Udzial

    data.Sector = data.Sector.str.removeprefix("WIG-")

    fig = px.treemap(
        data,
        path=[px.Constant("- - - I N D E K S Y - - -"), "Sector"],
        values="Udzial",
        color="Zmiana_pct",
        color_continuous_scale=["#CC0000", "#353535", "#00CC00"],
        custom_data=data[["Sector", "Zmiana_pct"]],
    )

    fig.update_traces(
        insidetextfont=dict(
            size=200,
        ),
        textfont=dict(size=40),
        textposition="middle center",
        texttemplate="<br>      %{customdata[0]}      <br><b>      %{customdata[1]:.2%}      </b>",
        marker_line_width=3,
        marker_line_color="#1a1a1a",
        root=dict(color="#1a1a1a"),
    )

    fig.update_coloraxes(showscale=True, cmin=-0.05, cmax=0.05, cmid=0)

    fig.update_layout(
        margin=dict(t=200, l=5, r=5, b=120),
        width=7680,
        height=4320,
        title=dict(
            text=f"INDEKSY SEKTOROWE WIG ⁕ {start:%d/%m} - {end:%d/%m} * {week_nr}w{start:%Y}",
            font=dict(
                color="white",
                size=150,
            ),
            yanchor="middle",
            xanchor="center",
            xref="paper",
            yref="paper",
            x=0.5,
        ),
        paper_bgcolor="#1a1a1a",
        colorway=["#D9202E", "#AC1B26", "#7F151D", "#3B6323", "#518A30", "#66B13C"],
        coloraxis_colorbar=dict(
            title="",
            thicknessmode="pixels",
            thickness=130,
            tickvals=[-0.049, 0.049],
            ticktext=["-5% ", "+5%"],
            orientation="v",
            tickfont=dict(
                color="white",
                size=55,
            ),
            ticklabelposition="inside",
        ),
    )

    fig.add_annotation(
        text=("source: Yahoo Finance"),
        x=0.90,
        y=-0.023,
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=(dt.now(tzinfo).strftime(r"%Y/%m/%d %H:%M")),
        x=0.1,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=("@SliwinskiAlan"),
        x=0.5,
        y=-0.025,
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    # fig.show()
    fig.write_image("wig_sectors_heatmap_1w_perf.png")

    data = data.sort_values("Zmiana_pct", ascending=False, ignore_index=True)

    data_string = ""
    for indx, (sector, _, _, change) in data.iterrows():
        if change > 0.005:
            data_string += f"{indx + 1}. 🟢"
        elif change > -0.005:
            data_string += f"{indx + 1}. ➖"
        else:
            data_string += f"{indx + 1}. 🔴"

        data_string += f" {sector:<6} -> {change:6.2%}\n"

        if indx == 4:
            break

    return data_string


def wig_do_chart():
    try:
        data = pd.read_html(
            "https://www.bankier.pl/inwestowanie/profile/quote.html?symbol=WIG",
            decimal=",",
            thousands="\xa0",
        )[1]

    except:
        return False

    data["Zmiana procentowa"] = data["Zmiana procentowa"].str.replace(",", ".")
    data["Zmiana procentowa"] = data["Zmiana procentowa"].str.rstrip("%").astype(float)
    data.drop(
        columns=["Zmiana", "Wpływ na indeks", "Udział w obrocie", "Udział w portfelu"],
        inplace=True,
    )
    data.rename({"Zmiana procentowa": "Zmiana_pct"}, axis=1, inplace=True)
    data.Zmiana_pct /= 100

    data["Udzial"] = data.Kurs * data.Pakiet

    data["udzial_zmiana_pct"] = data.Zmiana_pct * data.Udzial

    stat_chng = data.udzial_zmiana_pct.sum() / data.Udzial.sum()

    path = get_path('wig.csv')
    ticker_sector_industry = pd.read_csv(path)[["Ticker", "Sector", "Industry"]]

    data = pd.merge(data, ticker_sector_industry, how="left", on="Ticker")

    empty_tickers = data[data.Sector.isna()].Ticker + ".WA"

    if not empty_tickers.empty:
        empty_tickers_summary_profile = yq.Ticker(empty_tickers).summary_profile
        sector, industry = [], []
        for v in empty_tickers_summary_profile.values():
            sector.append(v["sector"])
            industry.append(v["industry"])

        rn = {
            "Financial Data & Stock Exchanges": "Financial Data<br>Stock Exchanges",
            "Utilities—Regulated Gas": "Regulated Gas",
            "Utilities—Independent Power Producers": "Independent<br>Power Producers",
            "Utilities—Renewable": "Renewable",
            "Utilities—Regulated Electric": "Regulated Electric",
            "Real Estate—Diversified": "Diversified",
            "Real Estate Services": "Services",
            "Real Estate—Development": "Development",
            "Farm & Heavy Construction Machinery": "Farm & Heavy<br>Construction Machinery",
            "Staffing & Employment Services": "Staffing & Employment<br>Services",
            "Tools & Accessories": "Tools<br>& Accessories",
            "Building Products & Equipment": "Building Products<br>& Equipment",
            "Integrated Freight & Logistics": "Integrated Freight<br>& Logistics",
            "Specialty Industrial Machinery": "Specialty<br>Industrial Machinery",
            "Electrical Equipment & Parts": "Electrical Equipment<br>& Parts",
            "Metal Fabrication": "Metal<br>Fabrication",
            "Aerospace & Defense": "Aerospace<br>& Defense",
            "Paper & Paper Products": "Paper<br>& Paper Products",
            "Specialty Chemicals": "Specialty<br>Chemicals",
            "Specialty Business Services": "Specialty<br>Business Services",
            "Drug Manufacturers—Specialty & Generic": "Drug Manufacturers<br>Specialty & Generic",
            "Medical Care Facilities": "Medical Care<br>Facilities",
            "Medical Instruments & Supplies": "Medical Instruments<br>& Supplies",
            "Pharmaceutical Retailers": "Pharmaceutical<br>Retailers",
            "Electronic Components": "Electronic<br>Components",
            "Scientific & Technical Instruments": "Scientific & Technical<br>Instruments",
            "Electronics & Computer Distribution": "Electronics<br>& Computer Distribution",
            "Furnishings, Fixtures & Appliances": "Furnishings, Fixtures<br>& Appliances",
            "Travel Services": "Travel<br<Services",
            "Information Technology Services": "Information Technology<br>Services",
            "Software—Infrastructure": "Software<br>Infrastructure",
            "Medical Devices": "Medical<br>Devices",
        }

        industry = [rn.get(ind, ind) for ind in industry]

        for indx, sec, inds in zip(empty_tickers.index, sector, industry):
            data.loc[indx, "Sector"] = sec
            data.loc[indx, "Industry"] = inds

    fig = px.treemap(
        data,
        path=[px.Constant("WIG"), "Sector", "Industry", "Ticker"],
        values="Udzial",
        color="Zmiana_pct",
        color_continuous_scale=["#CC0000", "#353535", "#00CC00"],
        custom_data=data[["Zmiana_pct", "Nazwa", "Ticker", "Kurs", "Sector"]],
    )

    fig.update_traces(
        insidetextfont=dict(
            size=120,
        ),
        textfont=dict(size=40),
        textposition="middle center",
        texttemplate="<br>%{customdata[2]}<br>    <b>%{customdata[0]:.2%}</b>     <br><sup><i>%{customdata[3]:.2f} zł</i><br></sup>",
        marker_line_width=3,
        marker_line_color="#1a1a1a",
        root=dict(color="#1a1a1a"),
    )

    fig.update_coloraxes(
        showscale=True,
        cmin=-0.03,
        cmax=0.03,
        cmid=0,
    )

    fig.update_layout(
        margin=dict(t=200, l=5, r=5, b=120),
        width=7680,
        height=4320,
        title=dict(
            text=f"INDEX WIG ⁕ {stat_chng:.2%} ⁕ {dt.now(tzinfo):%Y/%m/%d}",
            font=dict(
                color="white",
                size=150,
            ),
            yanchor="middle",
            xanchor="center",
            xref="paper",
            yref="paper",
            x=0.5,
        ),
        paper_bgcolor="#1a1a1a",
        # paper_bgcolor="rgba(0,0,0,0)",
        colorway=["#D9202E", "#AC1B26", "#7F151D", "#3B6323", "#518A30", "#66B13C"],
    )

    fig.add_annotation(
        text=("source: bankier.com"),
        x=0.90,
        y=-0.023,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=(dt.now(tzinfo).strftime(r"%Y/%m/%d %H:%M")),
        x=0.1,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=("@SliwinskiAlan"),
        x=0.5,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    # fig.show()
    fig.write_image("wig_heatmap.png")

    data["udzial_zmiana_pct"] = data.Udzial * data.Zmiana_pct
    sectors_change = (
        data.groupby("Sector")["udzial_zmiana_pct"].sum()
        / data.groupby("Sector")["Udzial"].sum()
    )

    sectors_change = sectors_change.sort_values(ascending=False)
    data = data.sort_values("Zmiana_pct", ascending=False)

    data_string = f"\nWIG perf 1D: {stat_chng:.2%}"

    if stat_chng > 0.02:
        data_string += " 🟢🟢🟢\n"
    elif stat_chng > 0.01:
        data_string += " 🟢🟢\n"
    elif stat_chng > 0.005:
        data_string += " 🟢\n"
    elif stat_chng > -0.005:
        data_string += " ➖\n"
    elif stat_chng > -0.01:
        data_string += " 🔴\n"
    elif stat_chng > -0.02:
        data_string += " 🔴🔴\n"
    else:
        data_string += " 🔴🔴🔴\n"

    data_string += f"\n🟢 {data.Ticker.iloc[0]} {data.Nazwa.iloc[0]} {data.Zmiana_pct.iloc[0]:.2%}\n🔴 {data.Ticker.iloc[-1]} {data.Nazwa.iloc[-1]} {data.Zmiana_pct.iloc[-1]:.2%}\n\n"

    for i, (sector, change) in enumerate(sectors_change.items()):
        if i < 3:
            data_string += f"{i+1}. {sector} ->{change:>7.2%}\n"

    return data_string


def wig_do_chart_1m_perf():
    try:
        data = pd.read_html(
            "https://www.bankier.pl/inwestowanie/profile/quote.html?symbol=WIG",
            decimal=",",
            thousands="\xa0",
        )[1]

    except:
        return False

    data.drop(
        columns=[
            "Zmiana",
            "Wpływ na indeks",
            "Udział w obrocie",
            "Udział w portfelu",
            "Zmiana procentowa",
            "Kurs",
        ],
        inplace=True,
    )

    tickers = data.Ticker.to_list()
    tickers = [f"{tick}.WA" for tick in tickers]

    stonks = yq.Ticker(tickers)

    start = (dt(dt.today().year, dt.today().month, 1) + timedelta(-1)).strftime(
        "%Y-%m-%d"
    )
    end = (dt.today().date()).strftime("%Y-%m-%d")
    yq_data = stonks.history(start=start, end=end)

    yq_data = yq_data.reset_index()[["symbol", "date", "adjclose"]]
    data_pivot = yq_data.pivot_table(values="adjclose", columns="symbol", index="date")
    changes = (data_pivot.pct_change() + 1).cumprod() - 1

    percentage_change = changes.tail(1).T
    percentage_change.columns = ["Zmiana_pct"]
    curr_prices = data_pivot.tail(1).T
    curr_prices.columns = ["Kurs"]

    merged = percentage_change.join(curr_prices)
    merged.index = merged.index.str.removesuffix(".WA")

    merged = merged.reset_index().rename({"symbol": "Ticker"}, axis=1)
    df = pd.merge(data, merged, on="Ticker")

    df["Udzial"] = df.Kurs * df.Pakiet
    df["udzial_zmiana_pct"] = df.Zmiana_pct * df.Udzial
    stat_chng = df.udzial_zmiana_pct.sum() / df.Udzial.sum()

    industry_sector_data = stonks.asset_profile

    sector, industry = [], []
    for v in industry_sector_data.values():
        sector.append(v["sector"])
        industry.append(v["industry"])

    rn = {
        "Financial Data & Stock Exchanges": "Financial Data<br>Stock Exchanges",
        "Utilities—Regulated Gas": "Regulated Gas",
        "Utilities—Independent Power Producers": "Independent<br>Power Producers",
        "Utilities—Renewable": "Renewable",
        "Utilities—Regulated Electric": "Regulated Electric",
        "Real Estate—Diversified": "Diversified",
        "Real Estate Services": "Services",
        "Real Estate—Development": "Development",
        "Farm & Heavy Construction Machinery": "Farm & Heavy<br>Construction Machinery",
        "Staffing & Employment Services": "Staffing & Employment<br>Services",
        "Tools & Accessories": "Tools<br>& Accessories",
        "Building Products & Equipment": "Building Products<br>& Equipment",
        "Integrated Freight & Logistics": "Integrated Freight<br>& Logistics",
        "Specialty Industrial Machinery": "Specialty<br>Industrial Machinery",
        "Electrical Equipment & Parts": "Electrical Equipment<br>& Parts",
        "Metal Fabrication": "Metal<br>Fabrication",
        "Aerospace & Defense": "Aerospace<br>& Defense",
        "Paper & Paper Products": "Paper<br>& Paper Products",
        "Specialty Chemicals": "Specialty<br>Chemicals",
        "Specialty Business Services": "Specialty<br>Business Services",
        "Drug Manufacturers—Specialty & Generic": "Drug Manufacturers<br>Specialty & Generic",
        "Medical Care Facilities": "Medical Care<br>Facilities",
        "Medical Instruments & Supplies": "Medical Instruments<br>& Supplies",
        "Pharmaceutical Retailers": "Pharmaceutical<br>Retailers",
        "Electronic Components": "Electronic<br>Components",
        "Scientific & Technical Instruments": "Scientific & Technical<br>Instruments",
        "Electronics & Computer Distribution": "Electronics<br>& Computer Distribution",
        "Furnishings, Fixtures & Appliances": "Furnishings, Fixtures<br>& Appliances",
        "Travel Services": "Travel<br<Services",
        "Information Technology Services": "Information Technology<br>Services",
        "Software—Infrastructure": "Software<br>Infrastructure",
        "Medical Devices": "Medical<br>Devices",
    }

    industry = [rn.get(ind, ind) for ind in industry]

    data["Sector"] = sector
    data["Industry"] = industry

    fig = px.treemap(
        data,
        path=[px.Constant("WIG"), "Sector", "Ticker"],
        values="Udzial",
        color="Zmiana_pct",
        color_continuous_scale=["#CC0000", "#353535", "#00CC00"],
        custom_data=data[["Zmiana_pct", "Nazwa", "Ticker", "Kurs", "Sector"]],
    )

    fig.update_traces(
        insidetextfont=dict(
            size=120,
        ),
        textfont=dict(size=40),
        textposition="middle center",
        texttemplate="<br>%{customdata[2]}<br>    <b>%{customdata[0]:.2%}</b>     <br><sup><i>%{customdata[3]:.2f} zł</i><br></sup>",
        marker_line_width=3,
        marker_line_color="#1a1a1a",
        root=dict(color="#1a1a1a"),
    )

    fig.update_coloraxes(
        showscale=True,
        cmin=-0.03,
        cmax=0.03,
        cmid=0,
    )

    fig.update_layout(
        margin=dict(t=200, l=5, r=5, b=120),
        width=7680,
        height=4320,
        title=dict(
            text=f"INDEX WIG ⁕ 1M perf: {stat_chng:.2%} ⁕ {dt.now(tzinfo):%Y/%m}",
            font=dict(
                color="white",
                size=150,
            ),
            yanchor="middle",
            xanchor="center",
            xref="paper",
            yref="paper",
            x=0.5,
        ),
        paper_bgcolor="#1a1a1a",
        colorway=["#D9202E", "#AC1B26", "#7F151D", "#3B6323", "#518A30", "#66B13C"],
    )

    fig.add_annotation(
        text=("source: Yahoo Finance"),
        x=0.90,
        y=-0.023,
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=(dt.now(tzinfo).strftime(r"%Y/%m/%d %H:%M")),
        x=0.1,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=("@SliwinskiAlan"),
        x=0.5,
        y=-0.025,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    # fig.show()
    fig.write_image("wig_heatmap_1m_perf.png")

    df["udzial_zmiana_pct"] = df.Udzial * df.Zmiana_pct
    sectors_change = (
        df.groupby("Sector")["udzial_zmiana_pct"].sum()
        / df.groupby("Sector")["Udzial"].sum()
    )

    sectors_change = sectors_change.sort_values(ascending=False)
    df = df.sort_values("Zmiana_pct", ascending=False)

    data_string = f"\nWIG perf 1M: {stat_chng:.2%}"

    if stat_chng > 0.15:
        data_string += " 🟢🟢🟢\n"
    elif stat_chng > 0.10:
        data_string += " 🟢🟢\n"
    elif stat_chng > 0.05:
        data_string += " 🟢\n"
    elif stat_chng > -0.05:
        data_string += " ➖\n"
    elif stat_chng > -0.10:
        data_string += " 🔴\n"
    elif stat_chng > -0.15:
        data_string += " 🔴🔴\n"
    else:
        data_string += " 🔴🔴🔴\n"

    data_string += f"\n🟢 {df.Ticker.iloc[0]} {df.Nazwa.iloc[0]} {df.Zmiana_pct.iloc[0]:.2%}\n🔴 {df.Ticker.iloc[-1]} {df.Nazwa.iloc[-1]} {df.Zmiana_pct.iloc[-1]:.2%}\n\n"

    for i, (sector, change) in enumerate(sectors_change.items()):
        if i < 3:
            data_string += f"{i+1}. {sector} ->{change:>7.2%}\n"

    return data_string


def wig_do_chart_1w_perf():
    today = dt.today()
    week_nr = today.isocalendar().week

    path = get_path('wig.csv')
    df = pd.read_csv(path)

    df.Ticker = df.Ticker + ".WA"

    prices = yq.Ticker(df.Ticker).history(period="1mo")[["adjclose"]].reset_index()

    prices = prices.pivot(columns="symbol", index="date").droplevel(level=0, axis=1)

    prices_chng = prices.reset_index()
    prices_chng.date = pd.to_datetime(prices_chng.date)
    prices_chng["week_nr"] = prices_chng.date.dt.isocalendar().week
    b = prices_chng[prices_chng.week_nr == week_nr]
    a = prices_chng[
        (prices_chng.week_nr == 52) | (prices_chng.week_nr == week_nr - 1)
    ].tail(1)
    prices_chng = pd.concat([a, b])

    start, end = prices_chng.date.iloc[1], prices_chng.date.iloc[-1]

    prices_chng = prices_chng.drop(columns=["date", "week_nr"])

    prices_chng = (prices_chng.pct_change() + 1).cumprod() - 1

    prices_chng = prices_chng.tail(1).T.reset_index()
    prices_chng.columns = ["Ticker", "Zmiana_pct"]

    kurs = prices.tail(1).T.reset_index()
    kurs.columns = ["Ticker", "Kurs"]

    df.Ticker = df.Ticker.str.removesuffix('.WA')
    kurs.Ticker = kurs.Ticker.str.removesuffix('.WA')
    prices_chng.Ticker = prices_chng.Ticker.str.removesuffix(".WA")

    full = pd.merge(df, prices_chng, on="Ticker")
    data = pd.merge(full, kurs, on="Ticker")

    data["Udzial"] = data.Kurs * data.Pakiet

    data["udzial_zmiana_pct"] = data.Zmiana_pct * data.Udzial

    stat_chng = data.udzial_zmiana_pct.sum() / data.Udzial.sum()

    data.Ticker = data.Ticker.str.removesuffix(".WA")

    fig = px.treemap(
        data,
        path=[px.Constant("WIG"), "Sector", "Industry", "Ticker"],
        values="Udzial",
        color="Zmiana_pct",
        color_continuous_scale=["#CC0000", "#353535", "#00CC00"],
        custom_data=data[["Zmiana_pct", "Nazwa", "Ticker", "Kurs", "Sector"]],
    )

    fig.update_traces(
        insidetextfont=dict(
            size=120,
        ),
        textfont=dict(size=40),
        textposition="middle center",
        texttemplate="<br>%{customdata[2]}<br>    <b>%{customdata[0]:.2%}</b>     <br><sup><i>%{customdata[3]:.2f} zł</i><br></sup>",
        marker_line_width=3,
        marker_line_color="#1a1a1a",
        root=dict(color="#1a1a1a"),
    )

    fig.update_coloraxes(
        showscale=True,
        cmin=-0.07,
        cmax=0.07,
        cmid=0,
    )

    fig.update_layout(
        margin=dict(t=200, l=5, r=5, b=120),
        width=7680,
        height=4320,
        title=dict(
            text=f"INDEX WIG ⁕ {stat_chng:.2%} ⁕ {start:%d/%m} - {end:%d/%m} * {week_nr}w{start:%Y}",
            font=dict(
                color="white",
                size=150,
            ),
            yanchor="middle",
            xanchor="center",
            xref="paper",
            yref="paper",
            x=0.5,
        ),
        paper_bgcolor="#1a1a1a",
        colorway=["#D9202E", "#AC1B26", "#7F151D", "#3B6323", "#518A30", "#66B13C"],
    )

    fig.add_annotation(
        text=("source: Yahoo Finance"),
        x=0.90,
        y=-0.023,  #
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=(dt.now(tzinfo).strftime(r"%Y/%m/%d %H:%M")),
        x=0.1,
        y=-0.025,
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    fig.add_annotation(
        text=("@SliwinskiAlan"),
        x=0.5,
        y=-0.025,
        font=dict(family="Calibri", size=80, color="white"),
        opacity=0.7,
        align="left",
    )

    # fig.show()
    fig.write_image("wig_heatmap_1w_perf.png")

    data["udzial_zmiana_pct"] = data.Udzial * data.Zmiana_pct
    sectors_change = (
        data.groupby("Sector")["udzial_zmiana_pct"].sum()
        / data.groupby("Sector")["Udzial"].sum()
    )

    sectors_change = sectors_change.sort_values(ascending=False)
    data = data.sort_values("Zmiana_pct", ascending=False)

    data_string = f"\nWIG perf 1W: {stat_chng:.2%}"

    if stat_chng > 0.05:
        data_string += " 🟢🟢🟢\n"
    elif stat_chng > 0.03:
        data_string += " 🟢🟢\n"
    elif stat_chng > 0.01:
        data_string += " 🟢\n"
    elif stat_chng > -0.01:
        data_string += " ➖\n"
    elif stat_chng > -0.03:
        data_string += " 🔴\n"
    elif stat_chng > -0.05:
        data_string += " 🔴🔴\n"
    else:
        data_string += " 🔴🔴🔴\n"

    data = data.dropna()

    data_string += f"\n🟢 {data.Ticker.iloc[0]} {data.Nazwa.iloc[0]} {data.Zmiana_pct.iloc[0]:.2%}\n🔴 {data.Ticker.iloc[-1]} {data.Nazwa.iloc[-1]} {data.Zmiana_pct.iloc[-1]:.2%}\n\n"

    for i, (sector, change) in enumerate(sectors_change.items()):
        if i < 3:
            data_string += f"{i+1}. {sector} ->{change:>7.2%}\n"

    return data_string


if __name__ == "__main__":
    wig20_do_chart()
