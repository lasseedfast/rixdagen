import traceback
from datetime import datetime

import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import requests
import sqlalchemy
import streamlit as st

from config import db_name
from config import db_user as user
from config import ip_server as ip
from config import pwd_postgres as pwd
from info import (
    explainer,
    limit_warning,
    months_conversion,
    party_colors,
    party_colors_lighten,
    select_columns,
    css,
)


class Params:
    """Containing params."""

    def __init__(self, params):
        self.params = params
        # Set parameters.
        self.q = self.set_param("q")
        self.parties = self.set_param("parties")
        self.persons = self.set_param("persons")
        self.from_year = self.set_param("from_year")
        self.to_year = self.set_param("to_year")
        self.debates = self.set_param("debates")

    def set_param(self, key):
        """Return value if in params."""
        if key in self.params:
            if key in ["parties", "persons", "debates"]:
                value = self.params[key][0].split(",")
            else:
                value = self.params[key][0]

        else:
            value = []
            if key == "q":
                value = ""
            elif key == "from_year":
                value = 1993  # Catch all.
            elif key == "to_year":
                value = 2030  # Catch all.
        return value

    def update(self):
        """Update parameters."""
        st.experimental_set_query_params(
            q=self.q,
            from_year=self.from_year,
            to_year=self.to_year,
            parties=",".join(self.parties),
            debates=",".join(self.debates),
            persons=",".join(self.persons),
        )

    def reset(self, q=False):
        for key in self.params:
            self.params[key] = []
        if q:
            self.q = q


def datestring_to_date(x):
    print(x)
    date_list = x.split(" ")
    return f"{date_list[2]}-{months_conversion[date_list[1]]}-{date_list[0]}"


def make_snippet(text, search_terms, long=False):
    """Find the word searched for and give it some context."""

    text = text.replace("Fru talman! ", "").replace("Herr talman! ", "")
    if search_terms == "speaker":
        if long:
            snippet = str(text[:300])
            if len(text) > 300:
                snippet += "..."
        else:
            snippet = str(text[:80]) + "..."
            if len(text) > 80:
                snippet += "..."
    else:
        snippet = []
        text_lower = text.lower()
        snippet_lenght = int(8 / len(search_terms))  # * Change to another value?
        if long:
            snippet_lenght = snippet_lenght * 4
        # Make the whole text to a list in lower cases.
        text_list = text.split(" ")
        text_list_lower = text_lower.split(" ")
        # Try to find each for searched for and add to the snippet.
        for word in search_terms:
            word = word.replace("*", "").strip().lower()
            if word in text_list_lower:
                position = text_list_lower.index(word)

                position_start = position - snippet_lenght
                if position_start < 0:
                    position_start = 0

                position_end = position + int(snippet_lenght / 2)
                if position_end > len(text_list_lower):
                    position_end = len(text_list_lower) - 1
                word_context_list = text_list[position_start:position_end]

                snippet.append(" ".join(word_context_list))

            elif word in text_lower:
                position = text_lower.find(word)
                # Find start position.
                if position - snippet_lenght * 5 < 0:
                    start_snippet = 0
                else:
                    start_snippet = text_lower.find(" ", position - snippet_lenght * 5)
                # Find end position.
                if position + len(word) + snippet_lenght * 4 > len(text):
                    end_snippet = len(text)
                else:
                    end_snippet = text_lower.find(
                        " ", position + len(word) + snippet_lenght * 4
                    )
                text = text[start_snippet:end_snippet]
                snippet.append(text)

            else:
                position = 0
                for listword in text_list:
                    position += 1
                    if word in listword.lower():
                        word_context_list = text_list[
                            position
                            - snippet_lenght : position
                            + int(snippet_lenght / 2)
                        ]
                        snippet.append(" ".join(word_context_list))

        snippet = "|".join(snippet)
        snippet = f"...{snippet}..."
    return snippet


def build_style_parties(parties):
    """Build a CSS styl for party names buttons."""
    style = "<style> "
    for party in parties:
        style += f' span[data-baseweb="tag"][aria-label="{party}, close by backspace"]{{ background-color: {party_colors[party]}}} .st-eg {{min-width: 14px;}} '  # max-width: 328px;
    style += "</style>"
    return style


def build_style_mps(mps):
    """Build a CSS styl for party names buttons."""
    style = "<style> "
    for mp in mps:
        party = mp[mp.find("(") + 1 : mp.find(")")].upper()
        party = fix_party(party)
        try:
            style += f' span[data-baseweb="tag"][aria-label="{mp}, close by backspace"]{{ background-color: {party_colors[party]};}} .st-eg {{min-width: 14px;}} '  # max-width: 328px;
        except KeyError:
            style += f' span[data-baseweb="tag"][aria-label="{mp}, close by backspace"]{{ background-color: {party_colors["-"]};}} .st-eg {{min-width: 14px;}} '
    style += "</style>"
    return style


def fix_party(party):
    """Replace old party codes with new ones."""
    party = party.upper().replace("KDS", "KD").replace("FP", "L")
    return party


def build_style_debate_types(debates):
    """Build a CSS style for debate type buttons."""
    style = "<style> "

    for debate in debates:
        style += f' span[data-baseweb="tag"][aria-label="{debate}, close by backspace"]{{ background-color: #767676;}} .st-eg {{min-width: 14px;}}'  # max-width: 328px;
    style += "</style>"
    return style


def highlight_cells(party):
    if party in party_colors.keys():
        color = party_colors[party]
        return f"background-color: {color}; font-weight: 'bold'"


@st.cache_data
def options_persons(df):
    d = {}
    for i in df.groupby("Talare"):
        d[i[0]] = i[1].shape[0]
    return [f"{key} - {value}" for key, value in d.items()]


@st.cache_data
def get_data(sql):
    """Get data from SQL database.

    Args:
        sql (str): A SQL query string.

    Returns:
        DataFrame: Dataframe with some adjustments to the data fetched from the DB.
    """
    df = pd.read_sql(sql, engine)

    if df.shape[0] not in [0, return_limit]:
        # Clean the data and change some column names.
        df["Parti"].replace("FP", "L", inplace=True)
        df["Parti"].replace("KDS", "Kd", inplace=True)
        df["debatetype"].replace("", "inte angiven debattyp", inplace=True)
        df["debatetype"].replace("-", "inte angiven debattyp", inplace=True)
        df["Anförande"] = df["Text"].apply(
            lambda x: x.replace("</p>", "").replace("</p>", " ").replace("-\n", " ")
        )
        df = df.loc[df["Parti"].isin(parties)]
        df["url_session"] = df["url_session"].apply(
            lambda x: "https://riksdagen.se" + str(x)
        )  # Add domain to url.

        df.sort_values(["Datum", "number"], axis=0, ascending=True, inplace=True)

        # Make snippets from the text field (short and long).
        df["Utdrag"] = df["Text"].apply(lambda x: make_snippet(x, search_terms))
        df["Utdrag_long"] = df["Text"].apply(
            lambda x: make_snippet(x, search_terms, long=True)
        )

    df.drop_duplicates(ignore_index=True, inplace=True)

    return df


@st.cache_data
def define_search_terms(user_input):
    """ Takes user input and make them into search terms for SQL.

    Args:
        user_input (str): The string resulting from user input (input()).

    Returns:
        list: List of search terms.
    """    
    # Search for quated phrases.
    search_terms = []
    while '"' in user_input:
        q1 = user_input.find('"')
        q2 = user_input.find('"', q1 + 1)
        quoted_term = user_input[q1 + 1 : q2]
        search_terms.append(quoted_term.lower())
        user_input = user_input.replace(f'"{quoted_term}"', "")
    while "  " in user_input:
        user_input = user_input.replace(
            "  ", " "
        ).strip()  # Remove double and trailing blanks.

    # Add non-quoted terms.
    if len(user_input) > 0:
        search_terms += [i.lower() for i in user_input.strip().split(" ")]
    return search_terms


def user_input_to_db(user_input, engine):
    """Writes user input to db for debugging."""
    sql = f"INSERT INTO  searches (id, search) VALUES ({datetime.timestamp(datetime.now())}, '{user_input}')"

    with engine.connect() as conn:
        conn.execute(sql)


def create_sql_query(search_terms):
    """Returns a valid sql query."""
    word_list = []
    years = ""
    for word in search_terms:
        
        # Check if years are specified.
        if "år:" in word:
            start = int(word[3:7])
            end = int(word[-4:])
            if start == end:
                years = [start]
            else:
                years = [str(i) for i in range(start, end + 1)]
            years_string = f"({', '.join(years)})"

        elif "*" not in word: #Searching for the exact word.
            word_list.append(f" {word} ")
        else:
            if word[0] == "*" and word[-1] == "*":
                word_list.append(word.replace("*", ""))
            elif word[0] == "*":
                word_list.append(f"{word.replace('*', '')} ")
            elif word[-1] == "*":
                word_list.append(f" {word.replace('*', '')}")
    
    # Format for SQL.
    search_list = [f"'%%{i}%%'" for i in word_list]

    n = 0
    for i in search_list:
        if " or " in i:
            search_list[n] = "OR"
        n += 1

    # Handle searches with OR.
    or_terms = []
    while "OR" in search_list:
        n_or = search_list.count("OR")
        or_terms.append(search_list.pop(search_list.index("OR") - 1))
        if n_or == 1:
            or_terms.append(search_list.pop(search_list.index("OR") + 1))
        search_list.remove("OR")
    or_sql = f"( text_lower LIKE {' OR text_lower LIKE '.join(or_terms)})"
    # Handle searches with -.
    not_terms = []
    for term in search_list:
        if "-" in term:  # TODO Make this not include words with hyphen.
            not_terms.append(search_list.pop(search_list.index(term)).replace("-", ""))

    # Create SQL query.
    search_sql = ''
    if search_list != []:
        search_sql = f'(text_lower LIKE {" AND text_lower LIKE ".join(search_list)}) '
    
    if or_terms != []:
        if search_sql == '':
            search_sql = or_sql
        else:
            search_sql = search_sql + " AND " + or_sql

    if len(not_terms) > 0:
        search_sql += (
            f' AND (text_lower NOT LIKE {" AND text_lower NOT LIKE ".join(not_terms)})'
        )
    if years != "": # Search for years.
        search_sql = f"({search_sql}) AND year in {years_string}"
    sql = f"SELECT {select_columns} FROM {db_name} WHERE {search_sql} LIMIT {return_limit}"
    
    return sql


def protocol_url(id):
    """Returns the url of the protocol."""
    url = f"https://data.riksdagen.se/dokument/{id}.json"
    try:
        documents = requests.get(url).json()["dokumentlista"]["dokument"]
        for document in documents:
            print(document)
            if document["dok_id"] == id:
                for file in document["filbilaga"]["fil"]:
                    if "prot" in file["namn"]:
                        url = file["url"]
    except:  # If there is no url to PDF.
        url = f"https://data.riksdagen.se/dokument/{id}"
    
    return url


def error2db(error, user_input, engine):
    """ Write error to DB for debugging."""
    df = pd.DataFrame(
        {
            "error": error,
            "time": datetime.date(datetime.now()),
            "user_input": str(user_input),
        },
        index=[0],
    )
    df.to_sql("errors", engine, if_exists="append", index=False)


@st.cache_data
def get_speakers():
    """ Get all """
    return pd.read_sql("select * from persons", engine)


def search_person(user_input, df_persons):
    """ Returns SQL query made for searching everything a defined speaker has said.

    Args:
        user_input (str): The string resulting from user input (input()).

    Returns:
        list: List of search terms.
    """    
    # List all alternatives.
    options = df_persons.loc[df_persons["name"] == user_input.lower()][
        "speaker"
    ].tolist()
    options = [f"Ja, sök på {i.title()}" for i in options]
    no_option = f"Nej, jag vill söka på vad soms sagts om {user_input.title()}."
    options += [no_option, "Välj ett alternativ"]
    preselected_option = len(options) - 1
    # Let the user select a person or no_alternative.
    speaker = st.selectbox(
        ":red[Vill du söka efter vad en specifik ledamot sagt?]",
        options,
        index=preselected_option,
    )

    if speaker == "Välj ett alternativ":
        st.stop()
    if speaker == no_option:
        search_terms = define_search_terms(user_input) # Return "normal" query if no_alternative.
        sql = create_sql_query(search_terms)
    else:
        speaker = speaker.replace("Ja, sök på ", "")
        sql = f"SELECT {select_columns} FROM {db_name} WHERE talare = '{speaker.title()}' LIMIT {return_limit}"
    return sql


# Title and explainer for streamlit
st.set_page_config(
    page_title="Rixdagen",
    page_icon="favicon.png",
    initial_sidebar_state="auto",
)
st.title("Vad säger de i Riksdagen?")
st.markdown(css, unsafe_allow_html=True)
# Get params from url.
params = Params(st.experimental_get_query_params())

# The official colors of the parties
parties = list(party_colors.keys())  # List of partycodes

# Max hits returned by db.
return_limit = 10000

# Ask for word to search for.
user_input = st.text_input(
    " ",
    value=params.q,
    placeholder="Sök ett ord, vilket som helst",
    # label_visibility="hidden",
    help='Du kan använda asterix (*), minus (-), citattecken ("") och OR.',
)
params.q = user_input

if len(user_input) > 2:
    try:
        engine = sqlalchemy.create_engine(
            f"postgresql://{user}:{pwd}@{ip}:5432/riksdagen"
        )
        user_input = user_input.replace("'", '"')

        # Put user input in session state (first run).
        if "user_input" not in st.session_state:
            st.session_state["user_input"] = user_input
            user_input_to_db(user_input, engine)
        else:
            if st.session_state["user_input"] != user_input:
                # Write user input to DB.
                st.session_state["user_input"] = user_input
                user_input_to_db(user_input, engine)
                # Reser url parameters.
                params.reset(q=user_input)

        params.update()

        # Check if user has searched for a specific politician.
        if len(user_input.split(" ")) in [2, 3, 4]: #TODO Better way of telling if name?
            df_persons = get_speakers() #TODO Get only unique values.
            list_persons = df_persons["name"].tolist()
            if user_input.lower() in list_persons:
                sql = search_person(user_input, df_persons)
                search_terms = "speaker"

        if "sql" not in globals():
            search_terms = define_search_terms(user_input)
            sql = create_sql_query(search_terms)

        # Fetch data from DB.
        df = get_data(sql)

        if len(df) == 0:  # If no hits.
            st.write("Inga träffar. Försök igen!")
            st.stop()
        elif df.shape[0] == 10000:
            st.write(limit_warning)
            st.stop()

        party_talks = pd.DataFrame(df["Parti"].value_counts())
        party_labels = party_talks.index.to_list()  # List with active parties.
        if type(party_labels) == "list":
            party_labels.sort()

        if search_terms != "speaker":
            # Let the user select parties to be included.
            container_parties = st.container()
            with container_parties:
                style_parties = build_style_parties(
                    party_labels
                )  # Make the options the right colors.
                st.markdown(style_parties, unsafe_allow_html=True)
                params.parties = st.multiselect(
                    label="Välj vilka partier som ska ingå",
                    options=party_labels,
                    default=party_labels,
                )
            if params.parties != []:
                df = df.loc[df["Parti"].isin(params.parties)]
                if len(df) == 0:
                    st.stop()

        # Let the user select type of debate.
        container_debate = st.container()
        with container_debate:
            debates = df["debatetype"].unique().tolist()
            debates.sort()

            style = build_style_debate_types(debates)
            st.markdown(style, unsafe_allow_html=True)
            params.debates = st.multiselect(
                label="Välj typ av debatt",
                options=debates,
                default=debates,
            )
        if params.debates != []:
            df = df.loc[df["debatetype"].isin(params.debates)]
            if len(df) == 0:
                st.stop()
        params.update()

        # Let the user select a range of years.
        from_year = int(params.from_year)
        to_year = int(params.to_year)
        df_ = df.loc[
            df["År"].isin([i for i in range(from_year, to_year)])
        ]  # TODO Ugly.
        years = list(range(int(df["År"].min()), int(df["År"].max()) + 1))
        if len(years) > 1:
            params.from_year, params.to_year = st.select_slider(
                "Välj tidsspann",
                list(range(int(df["År"].min()), int(df["År"].max()) + 1)),
                value=(years[0], years[-1]),
            )
            df = df.loc[
                df["År"].isin(list(range(params.from_year, params.to_year + 1)))
            ]
        elif len(years) == 1:
            df = df.loc[df["År"] == years[0]]

        params.update()

        if search_terms != "speaker":
            # Let the user select talkers.
            options = options_persons(df)
            style_mps = build_style_mps(options)  # Make the options the right colors.
            st.markdown(style_mps, unsafe_allow_html=True)
            col1_persons, col2_persons = st.columns([5, 2])
            # Sort alternatives in column to the right.
            with col2_persons:
                sort = st.selectbox(
                    "Sortera på", options=["Bokstavsordning", "Flest anföranden"]
                )
                if sort == "Flest anföranden":
                    options = sorted(
                        options,
                        key=lambda x: [int(i) for i in x.split() if i.isdigit()][-1],
                        reverse=True,
                    )
                else:
                    options.sort()
            # Present options in column to the left.
            with col1_persons:
                expand_persons = st.container()
                with expand_persons:
                    params.persons = st.multiselect(
                        label="Filtrera på personer",
                        options=options,
                        default=[],
                    )
            # Filter df.
            if params.persons != []:
                params.persons = [i[: i.find(")") + 1] for i in params.persons]
                df = df.loc[df["Talare"].isin(params.persons)]
        params.update()

        # Give df an index.
        df.index = range(1, df.shape[0] + 1)

        ##* Start render. *##

        st.markdown("---")  # Draw line after filtering.
        st.write(f"**Träffar: {df.shape[0]}**")

        ## Short snippets,
        expand_short = st.expander("Visa tabell med korta utdrag", expanded=False)
        with expand_short:
            st.dataframe(df[["Utdrag", "Parti"]].style.applymap(highlight_cells))

        ## Long snippets.
        expand_long = st.expander(
            "Visa tabell med längre utdrag (kan ta lång tid om många träffar).",
            expanded=False,
        )
        with expand_long:
            n = 0

            # st.markdown(style, unsafe_allow_html=True)
            # df["date"] = df["Datum"].apply(lambda x: datestring_to_date(x))
            df.sort_values(["Datum", "dok_id", "number"], axis=0, inplace=True)
            new_debate = True
            dok_id = None

            for row in df.iterrows():
                n += 1
                row = row[1]

                # Find out if it's a new debate.
                if row["dok_id"] == dok_id:
                    new_debate = False
                else:
                    new_debate = True
                dok_id = row["dok_id"]

                # Remove title for ministers. #TODO Remove "statsråd" etc.
                if "minister" in row["Talare"]:
                    row["Talare"] = row["Talare"][
                        row["Talare"].find("minister") + len("minister") :
                    ]

                # Write to table.

                if new_debate:
                    # st.write("---", unsafe_allow_html=True)
                    st.markdown(
                        f""" <span style="font-weight: bold;">{row['Datum']}</span> """,
                        unsafe_allow_html=True,
                    )
                col1, col2, col3 = st.columns([2, 7, 2])
                with col1:
                    st.write(f"{row['Talare']}", unsafe_allow_html=True)
                with col2:
                    snippet = (
                        row["Utdrag_long"]
                        .replace(":", "\:")
                        .replace("<p>", "")
                        .replace("</p>", "")
                    )
                    st.markdown(
                        f""" <span style="background-color:{party_colors_lighten[row['Parti']]}; color:black;">{snippet}</span> """,
                        unsafe_allow_html=True,
                    )
                with col3:
                    full_text = st.button("Fulltext", key=n)
                    if full_text:
                        with st.sidebar:
                            data_person = requests.get(
                                f'https://data.riksdagen.se/personlista/?iid={row["intressent_id"]}&utformat=json'
                            ).json()["personlista"]["person"]  
                            name_person = data_person["sorteringsnamn"].lower().replace(",", "-").replace(' ', '-')
                            url_person = f'https://www.riksdagen.se/sv/ledamoter-partier/ledamot/{name_person}_{row["intressent_id"]}'
                            st.markdown(
                                f""" <span class="{row['Parti']}" style="font-weight: bold;">[ {row['Talare']} ]({url_person})</span> """,
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f""" <span style="font-style: italic;">{row["Datum"]} - {row['debatetype']}</span> """,
                                unsafe_allow_html=True,
                            )
                            st.write(
                                row["Text"].replace(":", "\:"), unsafe_allow_html=True
                            )
                            if row["url_session"] != "https://riksdagen.se":
                                st.markdown(
                                    f'📺 [Se debatten i Riksdagen]({row["url_session"]})'
                                )
                            if row["url_audio"] != "":
                                h = str(int(int(row["start"]) / 3600))
                                m = str(int((int(row["start"]) % 3600) / 60))
                                if len(m) == 1:
                                    m = "0" + m
                                s = str(int((int(row["start"]) % 3600) % 60))
                                if len(s) == 1:
                                    s = "0" + s
                                start_time = ""
                                if h != "0":
                                    start_time += f"{h}:"
                                start_time += f"{m}:{s}"
                                st.markdown(
                                    f'💬 [Ladda ner ljudet]({row["url_audio"]}) (Anförandet börjar vid {start_time})'
                                )

                            url_protocol = protocol_url(dok_id)
                            st.markdown(f"📝 [Ladda ner protokollet]({url_protocol})")

        # Download all data in df.
        st.download_button(
            "Ladda ner datan som CSV",
            data=df.to_csv(
                index=False,
                sep=";",
                columns=[
                    "talk_id",
                    "Anförande",
                    "Parti",
                    "Talare",
                    "Datum",
                    "url_session",
                ],
            ).encode("utf-8"),
            file_name=f"{user_input}.csv",
            mime="text/csv",
        )

        # Remove talks from same party within the same session to make the
        # statistics more representative.
        df_ = df[["talk_id", "Parti", "År"]].drop_duplicates()

        if search_terms != "speaker":
            ## Make pie chart.
            party_talks = pd.DataFrame(df_["Parti"].value_counts())
            party_labels = party_talks.index.to_list()
            fig, ax1 = plt.subplots()
            total = party_talks["Parti"].sum()
            mentions = party_talks["Parti"]
            ax1.pie(
                mentions,
                labels=party_labels,
                autopct=lambda p: "{:.0f}".format(p * total / 100),
                colors=[party_colors[key] for key in party_labels],
                startangle=90,
            )

        # Make bars per year.
        years = set(df["År"].tolist())

        df_years = pd.DataFrame(columns=["Parti", "År"])
        for i in df.groupby("År"):
            dff = pd.DataFrame(data=i[1]["Parti"].value_counts())
            dff["År"] = str(i[0])
            df_years = pd.concat([df_years, dff])
        df_years["party_code"] = df_years.index
        df_years["color"] = df_years["party_code"].apply(lambda x: party_colors[x])
        df_years.rename(columns={"Parti": "Antal", "party_code": "Parti"}, inplace=True)

        chart = (
            alt.Chart(df_years)
            .mark_bar()
            .encode(
                x="År",
                y="Antal",
                color=alt.Color("color", scale=None),
                tooltip=["Parti", "Antal"],
            )
        )

        if search_terms == "speaker":
            st.altair_chart(chart, use_container_width=True)

        else:
            # Put the charts in a table.
            fig1, fig2 = st.columns(2)
            with fig1:
                st.pyplot(fig)
            with fig2:
                st.altair_chart(chart, use_container_width=True)

        # Get feedback.
        st.empty()
        feedback_container = st.empty()

        with feedback_container.container():
            feedback = st.text_area(
                "*Skriv gärna förslag på funktioner och förbättringar här!*"
            )
            send = st.button("Skicka")
            if len(feedback) > 2 and send:
                df = pd.DataFrame(
                    {"feedback": feedback, "time": datetime.date(datetime.now())},
                    index=[0],
                )
                df.to_sql("feedback", engine, if_exists="append", index=False)
                feedback_container.write("*Tack!*")
        params.update()
        # st.markdown("##")

    except Exception as e:
        if (
            e == "streamlit.runtime.scriptrunner.script_runner.StopException"
        ):  # If st.stop() is used.
            pass
        else:
            print(traceback.format_exc())
            error2db(traceback.format_exc(), user_input, engine)
            st.markdown(
                ":red[Något har blivit fel, jag försöker lösa det så snart som möjligt. Testa gärna att söka på något annat.]"
            )

expand_explainer = st.expander("*Vad är det här? Var kommer datan ifrån? Hur gör jag?*")
with expand_explainer:
    st.markdown(explainer)
