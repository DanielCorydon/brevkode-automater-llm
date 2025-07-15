import streamlit as st
import pandas as pd
import os
import logging
from components.agent import graph, load_excel_mapping
from components.tools import search_and_replace, replace_titels_with_nogle

# logging.basicConfig(level=logging.DEBUG)


# Function to load mappings from an uploaded Excel file
def load_uploaded_mappings(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, sheet_name=None)
        # Try to find the right sheet ("query" or first sheet)
        sheet = df["query"] if "query" in df else next(iter(df.values()))
        # Expect columns: "Titel" and "Nøgle"
        if "Titel" in sheet.columns and "Nøgle" in sheet.columns:
            return dict(zip(sheet["Titel"], sheet["Nøgle"])), None
        else:
            return {}, "Excel-filen mangler 'Titel' eller 'Nøgle' kolonner."
    except Exception as e:
        return {}, f"Fejl ved indlæsning af Excel-fil: {str(e)}"


st.set_page_config(page_title="Brevkoder-automater", layout="wide")
st.title("Brevkoder-automater")

with st.expander("Om denne app", expanded=False):
    st.markdown(
        """
    ### Brevkoder-automater
    
    Dette værktøj hjælper med at transformere tekst ved at erstatte koder eller titler med deres respektive nøgler. 
    Applikationen bruger en LangGraph agent til at udføre teksttransformationer baseret på AI.
    
    **Sådan bruges appen:**
    1. Upload en Excel-fil med titel/nøgle-koblinger eller brug standard-CSV-filen
    2. Upload et Word-dokument eller indtast tekst direkte
    3. Indtast en prompt til AI-assistenten om, hvordan teksten skal transformeres
    4. Klik på "Begin transformation" for at starte processen
    """
    )

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
# DEFAULT_INPUT_TEXT = """Vi skriver til dig, fordi skriv hvem der har givet os oplysninger har givet os nye oplysninger om
# If betingelse Borger enlig ved ældrecheck berettigelse”din” Else ”jeres” likvide formue efter den seneste opgørelse i
# brevet Skriv titel på brev og dato for udsendelse. De nye oplysninger ændrer ikke den seneste opgørelse af If betingelse
# Borger enlig ved ældrecheck berettigelse  ”din” Else ”jeres” likvide formue til ældrecheck Årstal indeværende år.
# """
DEFAULT_INPUT_TEXT = """Vi skriver til dig, fordi Peter har givet os nye oplysninger om If betingelse Borger enlig ved ældrecheck berettigelse”dine” Else ”din” likvide formue efter den seneste opgørelse i brevet "Goddag"""


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

# Information about available tools
with st.expander("Om tilgængelige værktøjer", expanded=True):
    st.markdown(
        """
    **Tilgængelige værktøjer i promptet:**
    
    1. **search_and_replace(text, search, replace)** - Erstatter alle forekomster af 'search' med 'replace' i teksten.
       - Eksempel: `Using the tool search_and_replace, replace all instances of 'Hello' with 'Goodbye' in the following text:`
    
    2. **replace_titels_with_nogle(text, replacement_template)** - Erstatter alle titler fra mapping-filen med en skabelon.
       - Brug `<NØGLE>` i skabelonen for at indsætte den tilsvarende nøgle.
       - Eksempel: `Using the tool replace_titels_with_nogle, replace all titles with '{{<NØGLE>}}' in the following text:`
    """
    )

# Define a variable for the default LLM prompt text
DEFAULT_LLM_PROMPT = """Du er brevkoder I en IT virksomhed og skal til at kode et brev ved hjælp af mergefields. Titel-Nøgle-parrene har dine function tools selv adgang til, men da der er virkelig mange, modtager du dem ikke selv hver gang.

Du modtager et ukodet stykke tekst, og skal udføre en række tekst-transformationer.
 
Brevet skal kodes med Mergefield kodestrenge. Hver gang der står If betingelse skal der indsættes en kodestreng. Det er vigtigt at du indsætter en kodestreng med nøgle hver gang du møder ordene ’’If betingelse’’ i brevet.  

Du skal også sørge for at lave et MERGEFIELD, hver gang der fremgår en tekstbid, der er = en Titel, hvor mergefieldet indeholder Nøglen.
 
If betingelse: { IF ''J'' ''{ MERGEFIELD Nøgle }'' ''Tekst input1'' ''Tekst input2'' }

Eksempel på perfekt transformation:
Før transformation:
"
Vi lægger desuden vægt på, at det også af afgørelsen om ældrecheck fremgik, at vi ved opgørelsen af din likvide formue havde hentet If betingelse Borger enlig ved ældrecheck berettigelse ” dine ” Else ”din og din samlever/ægtefælles” formueoplysninger fra seneste årsopgørelse fra Skattestyrelsen.
"
Efter transformation:
"
Vi lægger desuden vægt på, at det også af afgørelsen om ældrecheck fremgik, at vi ved opgørelsen af din likvide formue havde hentet { IF "J" "{ MERGEFIELD ab-borger-enlig-ved-aeldrecheck-berettigelse }" " dine" "din og din samlever/ægtefælles "  formueoplysninger fra seneste årsopgørelse fra Skattestyrelsen."""

llm_prompt = st.text_area(
    "Indsæt LLM prompt her",
    value=DEFAULT_LLM_PROMPT,
    height=120,
    key="llm_prompt_input",
)

if st.button("Begin transformation"):
    try:
        if uploaded_docx is not None:
            st.error("Word document processing not implemented yet")
        else:
            # Create a combined prompt with instructions and text to process
            combined_prompt = f"{llm_prompt}\n\nText to process:\n{input_text}"

            # Display a spinner while processing
            with st.spinner("Processing text with AI..."):
                # Create placeholder for streaming output
                result_placeholder = st.empty()
                transformed_text = ""

                # Stream results from the agent
                for event in graph.stream(
                    {"messages": [{"role": "user", "content": combined_prompt}]}
                ):
                    for value in event.values():
                        if value["messages"] and len(value["messages"]) > 0:
                            latest_message = value["messages"][-1].content
                            if latest_message:
                                transformed_text = latest_message
                                result_placeholder.markdown(
                                    f"**Processing output:**\n{transformed_text}"
                                )

                # Final output display
                st.success("Transformation complete!")
                st.subheader("Result:")
                st.markdown(transformed_text)

    except Exception as e:
        st.error(f"Error during transformation: {str(e)}")
