# RDF and SPARQL Demo

This directory contains a quick hands-on demo to help you understand the basics of **RDF** (Resource Description Framework) and **SPARQL** (SPARQL Protocol and RDF Query Language).

## What is RDF?
RDF is a standard model for data interchange on the Web. It represents data in the form of **Triples**:
- **Subject**: The thing being described (e.g., Alice)
- **Predicate**: The property or relationship (e.g., knows)
- **Object**: The value or another thing (e.g., Bob)

Together: `Alice -> knows -> Bob`. This forms a **directed, labeled graph**. 

In our demo, we use a format called **Turtle** (`.ttl`), which is a human-readable way to write RDF triples.

## What is SPARQL?
SPARQL is the standard query language used to query RDF graphs. It looks a bit like SQL, but instead of querying tables, you are querying graph patterns. You specify the "shape" of the graph you want to find using variables (prefixed with `?`).

For example, to find all people and their names:
```sparql
SELECT ?person ?name
WHERE {
    ?person foaf:name ?name .
}
```

## How to run the demo

This demo uses `rdflib`, a popular Python library for working with RDF.

1. Navigate to this directory in your terminal:
   ```powershell
   cd d:\Programming-Projects\LoanOps-Agent\rdf_demo
   ```

2. If `rdflib` is not installed, install it via:
   ```powershell
   uv pip install rdflib
   # Or using standard pip depending on your environment setup:
   # pip install rdflib
   ```

3. Run the script:
   ```powershell
   python demo.py
   ```

Read through the `demo.py` source code! It has commented examples showing how to construct an RDF graph from raw text, and how to write basic SPARQL queries to query it.
