import streamlit as st
import json
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components
from retriever import Layer10EliteRetriever

# CONFIGURATION & STYLING
st.set_page_config(page_title="Layer10 Grounded Memory", layout="wide")
st.title("Layer10: Grounded Long-Term Memory Explorer")

# DATA LOADING 
@st.cache_data
def load_all_data():
    with open("Data/final_memory_graph.json", "r") as f:
        graph_data = json.load(f)
    with open("Data/canonicalized_entities.json", "r") as f:
        entity_data = json.load(f)
    return graph_data, entity_data

graph_data, entity_data = load_all_data()

# Initialize Retriever
@st.cache_resource
def get_retriever():
    return Layer10EliteRetriever("Data/final_memory_graph.json", "YOUR_GROQ_KEY")

retriever = get_retriever()

# SIDEBAR FILTERS & SEARCH 
st.sidebar.header("Search & Filter")
query = st.sidebar.text_input("Ask the Memory a question:")
all_entity_types = list(set(details['type'] for details in entity_data.values()))
selected_types = st.sidebar.multiselect(
    "Filter Entity Types:",
    options=all_entity_types,
    default=all_entity_types[:5] # This selects the first 5 types by default
)
st.sidebar.divider()
confidence_threshold = st.sidebar.slider(
    "Filter by Minimum Confidence:",
    min_value=0.0, max_value=1.0, value=0.5, step=0.1
)
show_historical = st.sidebar.checkbox("Show Historical/Superseded Claims", value=True)

# MAIN LAYOUT (Tabs)
tab1, tab2, tab3 = st.tabs(["Memory Graph", "Fact Explorer", "Audit Log"])

# GRAPH VIEW (Requirement: Navigate entities/claims)
with tab1:
    st.subheader("Interactive Knowledge Graph")
    st.caption("Blue = Entities | Green = Current Claims | Red = Historical | Grey = Sources")
    
    net = Network(height="600px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    display_limit = 30
    for i, fact in enumerate(graph_data[:display_limit]):
        if not show_historical and not fact.get('is_current'): continue
        if fact.get('confidence', 1.0) < confidence_threshold: continue
        
        entity = fact['entity']
        claim_text = fact['text']
        claim_short = claim_text[:30] + "..."
        
        #  ADD ENTITY NODE
        net.add_node(entity, label=entity, color="#4d94ff", size=25, shape="ellipse")
        
        # ADD CLAIM NODE
        status_color = "#00ffcc" if fact.get('is_current') else "#ff4b4b"
        hover_info = f"FACT: {claim_text}\nSTATUS: {fact['status']}\nCONFIDENCE: {fact.get('confidence', 0.9)}"
        net.add_node(claim_short, label=claim_short, color=status_color, size=15, title=hover_info)
        
        # Link Entity to Claim
        net.add_edge(entity, claim_short, label="asserts")

        # ADD SOURCE NODES (The "Grounding" Nodes)
        # To avoid a messy graph, we only show the primary source in the visual
        primary_source = fact['evidence'][0]['source']
        source_label = primary_source.split('/')[-1][:15] + "..." 
        
        # Grey node for the Source Artifact
        net.add_node(primary_source, label=source_label, color="#777777", size=10, shape="dot", title=f"Source: {primary_source}")
        
        # Link Claim to Source (This is the 'Evidence' edge)
        net.add_edge(claim_short, primary_source, label="evidenced_by", dashes=True)

    net.save_graph("temp_graph.html")
    components.html(open("temp_graph.html", 'r').read(), height=650)

# TAB 2: FACT EXPLORER (Search and Grounding) 
with tab2:
    if query:
        # SEARCH MODE: Triggered when you type in the sidebar
        st.write(f"### Results for: '{query}'")
        results = retriever.query(query)
        
        if not results['memories']:
            st.warning("No grounded memory matches found.")
        else:
            for m in results['memories']:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Fact:** {m['fact']}")
                        st.caption(f"Status: {m['status']} | Confidence: {m['confidence']}")
                    # Inside tab2, inside the results loop:
                    with col2:
                        if st.button("View Evidence", key=f"btn_{m['fact']}"):
                            st.write("---")
                            # Loop through ALL grounding sources returned by the new retriever
                            for i, g in enumerate(m['all_grounding']):
                                st.markdown(f"**Source {i+1}**")
                                st.info(f"\"{g['quote']}\"")
                                
                                # Use the URL cleaner we built earlier
                                clean_url = str(g['source_url']).strip('"').strip("'").replace('\\', '')
                                st.caption(f"📅 Verified: {g['timestamp']}")
                                st.markdown(f"🔗 [Open GitHub Issue]({clean_url})")
                                st.divider()
    else:
        # BROWSE MODE: Shows all entities when search is empty
        st.info("💡 Enter a question in the sidebar or browse entities below.")
        
        for ent_name, details in entity_data.items():
            # Check if entity matches the sidebar filters
            if details['type'] in selected_types:
                with st.expander(f"🏢 {ent_name} ({details['type']})"):
                    first_mention = details['mentions_log'][0]
                    mention_date = first_mention.get('timestamp') or first_mention.get('time') or "Unknown Date"
                    st.write(f"**First Seen:** {mention_date}")
                    st.write("**Known Aliases:** " + ", ".join(details['aliases']))
                    
                    # BROWSE CLAIMS FOR THIS ENTITY 
                    st.markdown("---")
                    entity_claims = [f for f in graph_data if f['entity'] == ent_name]
                    for ec in entity_claims:
                        # Apply Historical Filter
                        if not show_historical and not ec.get('is_current'):
                            continue
                        
                        st.markdown(f"✅ {ec['text']}")
                        
                        # CLEAN THE URL FOR BROWSE CLAIMS
                        raw_source = ec['evidence'][0]['source']
                        clean_source = str(raw_source).strip('"').strip("'").replace('\\', '')
                        st.caption(f"Source: {clean_source}")

#  TAB 3: AUDIT LOG (Requirement: Inspect duplicates/merges)
with tab3:
    st.subheader("Merge & Reversibility Audit")
    
    # PART 1: CLAIM AUDIT (Your existing code) 
    fact_to_audit = st.selectbox("Select a claim to inspect lineage:", options=[f['text'] for f in graph_data])
    
    selected_fact = next(f for f in graph_data if f['text'] == fact_to_audit)
    
    st.write("### Decision History")
    if not selected_fact.get('merge_history'):
        st.write("This claim was extracted directly and has no merges.")
    else:
        for history in selected_fact['merge_history']:
            orig_text = history.get('original_text') or history.get('original_extracted_text') or "No text recorded"
            st.warning(f"**Merged Original Text:** {orig_text}")
            st.write(f"**Reason:** {history['reason']}")
            m_time = history.get('timestamp') or "Date not recorded"
            st.write(f"**Timestamp:** {m_time}")
            st.divider()

    st.write("### Supporting Evidence Bundle")
    st.table(pd.DataFrame(selected_fact['evidence']))

    # PART 2: ENTITY AUDIT (NEW ADDON STARTS HERE)
    st.markdown("---") 
    st.subheader(" Entity Identity Resolution (Aliases)")
    st.write("Inspect how different names/spellings were merged into single Canonical Entities.")
    
    entity_to_audit = st.selectbox(
        "Select an entity to view its identity history:", 
        options=sorted(list(entity_data.keys()))
    )

    if entity_to_audit:
        ent_details = entity_data[entity_to_audit]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Official Name:** `{entity_to_audit}`")
            st.write(f"**Type:** {ent_details.get('type', 'General')}")
        with col2:
            st.write("**Total Mention Count:**")
            st.metric("Mentions", ent_details.get('total_mentions', 0))

        st.write("**Identified Aliases & Variations:**")
        # Shows a list of all the different ways this entity appeared in the data
        st.info(", ".join(ent_details.get('aliases', [])))

        with st.expander(" View Full Provenance Log (Source History)"):
            st.write("This log shows every instance this entity was mentioned and which original name was used.")
            # Convert the mentions_log into a nice table
            prov_df = pd.DataFrame(ent_details.get('mentions_log', []))
            st.dataframe(prov_df, use_container_width=True)