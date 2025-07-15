import streamlit as st
import pandas as pd
import os
import logging
from components.tools import text_to_word_docx, convert_text_to_mergefields

# from components.agent import graph, load_excel_mapping
# from components.tools import search_and_replace, replace_titels_with_nogle

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
    
    Dette værktøj hjælper med at kode tekst ved at erstatte koder eller titler med deres respektive nøgler. 
    Applikationen bruger en LangGraph agent til at udføre tekstkodning baseret på AI.
    
    **Sådan bruges appen:**
    1. Upload en Excel-fil med titel/nøgle-koblinger eller brug standard-CSV-filen
    2. Upload et Word-dokument eller indtast tekst direkte
    3. Indtast en prompt til AI-assistenten om, hvordan teksten skal kodes
    4. Klik på "Begin kodning" for at starte processen
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
DEFAULT_INPUT_TEXT = """Vi lægger desuden vægt på, at det også af afgørelsen om ældrecheck fremgik, at vi ved opgørelsen af din likvide formue havde hentet If betingelse Borger enlig ved ældrecheck berettigelse ” dine ” Else ”din og din samlever/ægtefælles” formueoplysninger fra seneste årsopgørelse fra Skattestyrelsen."""


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
st.subheader("3. Sprogmodel-prompt og Kodning")

# Information about available tools
with st.expander("Om tilgængelige værktøjer", expanded=True):
    st.markdown(
        """
    **Værktøjer, du kan bruge i din besked:**
    
    1. **Find og erstat ord** – Med dette værktøj kan du bede om at få et bestemt ord eller en sætning i teksten skiftet ud med noget andet. For eksempel: Hvis du vil have alle steder, hvor der står "Hej", ændret til "Farvel", så kan du bare skrive det i din besked.
    
    2. **Skift titler ud med koder** – Dette værktøj kan automatisk finde alle de titler, der står i din koblingsfil (listen med titler og koder), og bytte dem ud med deres tilhørende kode. Du kan også selv bestemme, hvordan koden skal se ud i teksten. For eksempel: Hvis du vil have alle titler udskiftet med noget andet, kan du skrive det i din besked.
    
    Du behøver ikke kende til programmering eller funktioner – bare fortæl, hvad du ønsker, så klarer værktøjerne resten for dig.
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


# Dynamically set the height based on the number of lines in the prompt (min 6, max 30 lines)
def get_textarea_height(text, min_height=120, max_height=600, line_height=22):
    num_lines = text.count("\n") + 1
    height = min_height + (num_lines - 6) * line_height if num_lines > 6 else min_height
    return min(max(height, min_height), max_height)


llm_prompt = st.text_area(
    "Indsæt sprogmodel-prompt her",
    value=DEFAULT_LLM_PROMPT,
    height=get_textarea_height(DEFAULT_LLM_PROMPT),
    key="llm_prompt_input",
)


# Session state to store the output for download
def get_mock_result(input_text):
    return (
        "**[EKSEMPEL PÅ RESULTAT]**\n"
        "Dette er kun et eksempel. Teksten er ikke blevet ændret af et rigtigt program.\n\n"
        f"Din originale tekst:\n{input_text}\n\n"
        "[Her ville du normalt se den færdige, ændrede tekst, når værktøjet er klar.]. Et eksempel på en kodning af det ovenstående kunne være:\n\n"
        'Vi lægger desuden vægt på, at det også af afgørelsen om ældrecheck fremgik, at vi ved opgørelsen af din likvide formue havde hentet { IF "J" "{ MERGEFIELD ab-borger-enlig-ved-aeldrecheck-berettigelse }" "dine" "din og din samlever/ægtefælles" } formueoplysninger fra seneste årsopgørelse fra Skattestyrelsen.'
    )


if "kodning_output" not in st.session_state:
    st.session_state["kodning_output"] = None


if st.button("Start kodning"):
    try:
        if uploaded_docx is not None:
            # Process the uploaded Word document (mock: just extract text, real: would use LLM/agent)
            # For demo, just use the mock result and write it to a .docx, then convert mergefields
            with st.spinner("Word-dokument behandles og mergefields indsættes..."):
                import tempfile

                # Generate mock result with special focus on the exact IF pattern example
                mock_result = 'Vi lægger desuden vægt på, at det også af afgørelsen om ældrecheck fremgik, at vi ved opgørelsen af din likvide formue havde hentet { IF "J" "{ MERGEFIELD ab-borger-enlig-ved-aeldrecheck-berettigelse }" "dine" "din og din samlever/ægtefælles" } formueoplysninger fra seneste årsopgørelse fra Skattestyrelsen.'

                # Save mock result as docx
                # Create a temporary file
                import os

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".docx"
                ) as tmp_docx:
                    tmp_path = tmp_docx.name

                try:
                    # Convert text to Word document
                    text_to_word_docx(mock_result, tmp_path)

                    # Convert mergefield-like text to real mergefields
                    success, debug_info = convert_text_to_mergefields(
                        tmp_path, tmp_path
                    )

                    # Read the bytes for download
                    with open(tmp_path, "rb") as f:
                        doc_bytes = f.read()

                    if success:
                        st.success(
                            f"Word-dokument med mergefields er klar til download!"
                        )
                        st.session_state["kodning_docx_bytes"] = doc_bytes
                    else:
                        st.warning(
                            f"Bemærk: Ingen felter blev konverteret. {debug_info}"
                        )
                        st.session_state["kodning_docx_bytes"] = doc_bytes

                    st.session_state["kodning_output"] = (
                        None  # No text output for Word doc
                    )

                except Exception as e:
                    st.error(f"Fejl under konvertering: {str(e)}")
                    import traceback

                    st.error(f"Detaljer: {traceback.format_exc()}")
                finally:
                    # Clean up the temporary file
                    if os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
        else:
            # --- Sprogmodel/agent kode (udkommenteret for demo/eksempeltilstand) ---
            # combined_prompt = f"{llm_prompt}\n\nText to process:\n{input_text}"
            # with st.spinner("Teksten behandles med sprogmodel..."):
            #     result_placeholder = st.empty()
            #     transformed_text = ""
            #     for event in graph.stream(
            #         {"messages": [{"role": "user", "content": combined_prompt}]}
            #     ):
            #         for value in event.values():
            #             if value["messages"] and len(value["messages"]) > 0:
            #                 latest_message = value["messages"][-1].content
            #                 if latest_message:
            #                     transformed_text = latest_message
            #                     result_placeholder.markdown(
            #                         f"**Behandlingens resultat:**\n{transformed_text}"
            #                     )
            #     st.success("Transformationen er færdig!")
            #     st.subheader("Resultat:")
            #     st.markdown(transformed_text)

            # --- Mock transformation instead of LLM/agent ---
            with st.spinner("Teksten behandles (demotilstand)..."):
                mock_result = get_mock_result(input_text)
                st.session_state["kodning_output"] = mock_result

                # Create a temporary docx for conversion
                import tempfile

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".docx"
                ) as tmp_docx:
                    text_to_word_docx(mock_result, tmp_docx.name)
                    try:
                        # Convert mergefield-like text to real mergefields
                        success, debug_info = convert_text_to_mergefields(
                            tmp_docx.name, tmp_docx.name
                        )
                        # Read the bytes for download
                        with open(tmp_docx.name, "rb") as f:
                            doc_bytes = f.read()

                        st.session_state["kodning_docx_bytes"] = doc_bytes

                        # if success:
                        #     st.success(f"Eksempel på kodning er færdig! {debug_info if debug_info else ''}")
                        # else:
                        #     st.warning(f"Ingen mergefields blev fundet i teksten. {debug_info if debug_info else ''}")
                    except Exception as e:
                        st.error(f"Fejl under konvertering af mergefields: {str(e)}")
                        import traceback

                        st.error(f"Detaljer: {traceback.format_exc()}")
    except Exception as e:
        st.error(f"Error during mock kodning: {str(e)}")
        st.session_state["kodning_output"] = None
        st.session_state["kodning_docx_bytes"] = None

# Only show the download button if output exists
if st.session_state.get("kodning_output"):
    # Always show the output text
    st.markdown(st.session_state["kodning_output"])

if st.session_state.get("kodning_docx_bytes"):
    st.download_button(
        label="Download som Word-dokument",
        data=st.session_state["kodning_docx_bytes"],
        file_name="transformed_text.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
