import json
from retriever import Layer10EliteRetriever
from config import GROQ_API_KEY # Ensure your config.py is set up

def generate_examples():
    # 1. Initialize the Elite Retriever
    # Using the final graph we built in Phase 3
    retriever = Layer10EliteRetriever("Data/final_memory_graph.json", GROQ_API_KEY)

    # 2. Define our Strategic Questions
    questions = [
        "What is the current status of the React setup on Windows?",
        "Tell me about the compilation issues found on Gentoo.",
        "How do I bake a chocolate cake?"
    ]

    context_packs = []

    print("Generating Context Packs for Layer10 evaluation...")

    for q in questions:
        print(f" > Processing: {q}")
        # Use the query method we built in Phase 5
        result = retriever.query(q)
        context_packs.append(result)

    # 3. Save to the final output file required by the brief
    output_file = "Data/example_context_packs.json"
    with open(output_file, "w") as f:
        json.dump(context_packs, f, indent=4)

    print(f"\nSUCCESS! {len(context_packs)} Context Packs saved to {output_file}")

if __name__ == "__main__":
    generate_examples()