import streamlit as st
import pandas as pd
import os
from components.mappings import load_uploaded_mappings
from components.azure_openai_controller import AzureOpenAIController

st.set_page_config(page_title="Brevkoder-automater", layout="wide")
st.title("Brevkoder-automater")

# Load default mapping from CSV at startup
default_mapping_path = os.path.join("documents", "Liste over alle nøgler.csv")
default_mappings = None
if os.path.exists(default_mapping_path):
    try:
        df_default = pd.read_csv(default_mapping_path, sep=";")
        if "Titel" in df_default.columns and "Nøgle" in df_default.columns:
            default_mappings = {
                row["Titel"]: row["Nøgle"] for _, row in df_default.iterrows()
            }
    except Exception as e:
        st.error(f"Fejl ved indlæsning af standard-CSV: {str(e)}")

st.subheader("1. Upload Excel-fil med Titel/Nøgle-koblinger")

if default_mappings:
    st.info(
        "En standard-CSV-fil bruges allerede, men du kan uploade din egen Excel-fil, hvis du mener, at filen er forkert eller forældet."
    )

uploaded_file = st.file_uploader("Vælg en Excel-fil", type=["xlsx"])

mappings = None
if uploaded_file is not None:
    mappings, error = load_uploaded_mappings(uploaded_file)
    if error:
        st.error(error)
    else:
        st.write("Antal koblinger fundet:", len(mappings))
        with st.expander("Vis titel/nøgle-par (fra uploadet fil)", expanded=False):
            st.dataframe(
                pd.DataFrame(list(mappings.items()), columns=["Titel", "Nøgle"]),
                hide_index=True,
            )
elif default_mappings:
    st.write("Antal koblinger fundet:", len(default_mappings))
    with st.expander("Vis titel/nøgle-par (fra standardfil)", expanded=False):
        st.dataframe(
            pd.DataFrame(list(default_mappings.items()), columns=["Titel", "Nøgle"]),
            hide_index=True,
        )
    mappings = default_mappings
else:
    st.info("Upload venligst en Excel-fil med koblinger.")

# --- Ny sektion: Upload Word-dokument eller indtast tekst ---
st.subheader("2. Upload Word-dokument eller indtast tekst")


# Define a variable for the default input text
DEFAULT_INPUT_TEXT = """Vi skriver til dig, fordi skriv hvem der har givet os oplysninger har givet os nye oplysninger om 
If betingelse Borger enlig ved ældrecheck berettigelse”din” Else ”jeres” likvide formue efter den seneste opgørelse i 
brevet Skriv titel på brev og dato for udsendelse. De nye oplysninger ændrer ikke den seneste opgørelse af If betingelse 
Borger enlig ved ældrecheck berettigelse  ”din” Else ”jeres” likvide formue til ældrecheck Årstal indeværende år.
"""

col1, col2 = st.columns(2)
with col1:
    uploaded_docx = st.file_uploader(
        "Vælg et Word-dokument", type=["docx", "docm"], key="word_upload"
    )
with col2:
    input_text = st.text_area(
        "Eller indtast tekst her",
        value=DEFAULT_INPUT_TEXT,
        height=200,
        key="text_input",
    )

if uploaded_docx is not None:
    st.success(f"Word-dokument uploadet: {uploaded_docx.name}")
    # Her kan du tilføje behandling af Word-dokumentet
elif input_text.strip():
    st.success("Tekst indtastet.")
    # Her kan du tilføje behandling af den indtastede tekst
else:
    st.info("Upload et Word-dokument eller indtast tekst for at fortsætte.")

# --- Ny sektion: LLM Prompt og Transformation ---
st.subheader("3. LLM Prompt og Transformation")


# Define a variable for the default LLM prompt text
DEFAULT_LLM_PROMPT = "Skriv de første 3 ord du modtog"

llm_prompt = st.text_area(
    "Indsæt LLM prompt her",
    value=DEFAULT_LLM_PROMPT,
    height=120,
    key="llm_prompt_input",
)

if st.button("Begin transformation"):
    # Instantiate the AzureOpenAIController (env vars or .env recommended)
    try:
        llm = AzureOpenAIController()
        # Use input_text from above and llm_prompt
        if uploaded_docx is not None:
            st.warning(
                "Word-dokument support er ikke implementeret endnu. Brug tekstfeltet."
            )
            input_for_llm = None
        else:
            input_for_llm = input_text.strip()
        if input_for_llm:
            with st.spinner("Kører LLM transformation..."):
                try:
                    prompt = f"{llm_prompt}\n\nInput:\n{input_for_llm}"
                    llm_response = llm.call_nano_model(prompt)
                    st.success("Transformation gennemført!")
                    st.text_area(
                        "LLM output (kopiér herfra)",
                        value=llm_response,
                        height=200,
                        key="llm_output",
                    )
                except Exception as e:
                    st.error(f"Fejl ved LLM-kald: {e}")
        else:
            st.warning("Indtast tekst eller upload et dokument først.")
    except Exception as e:
        st.error(f"Fejl ved initialisering af LLM: {e}")
