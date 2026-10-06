import rdflib

def main():
    print("Initializing RDF Graph...")
    # 1. Create an empty Graph
    g = rdflib.Graph()

    # 2. Define our data in Turtle format
    # Turtle is a syntax for expressing RDF data that is easy for humans to read.
    # It represents data as "subject predicate object ." triples.
    rdf_data = """
    @prefix ex: <http://example.org/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .

    ex:Alice foaf:name "Alice" ;
             foaf:age 30 ;
             foaf:knows ex:Bob .

    ex:Bob foaf:name "Bob" ;
           foaf:age 25 ;
           foaf:knows ex:Charlie .

    ex:Charlie foaf:name "Charlie" ;
               foaf:age 28 .
    """

    # Load the Turtle data into our graph
    g.parse(data=rdf_data, format="turtle")
    print(f"Graph loaded successfully with {len(g)} statements/triples.\n")

    # 3. Query the Graph with SPARQL
    # SPARQL is the standard query language for RDF databases.
    
    # --- Example 1: Find all people and their names ---
    print("--- Query 1: Find all people and their names ---")
    query1 = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?person ?name
    WHERE {
        ?person foaf:name ?name .
    }
    """
    
    results1 = g.query(query1)
    for row in results1:
        print(f"Person URI: {row.person} | Name: {row.name}")
    print("\n")


    # --- Example 2: Graph Traversal (Find who Alice knows) ---
    print("--- Query 2: Find who Alice knows (Graph Traversal) ---")
    query2 = """
    PREFIX ex: <http://example.org/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?friendName
    WHERE {
        ex:Alice foaf:knows ?friend .
        ?friend foaf:name ?friendName .
    }
    """
    
    results2 = g.query(query2)
    for row in results2:
        print(f"Alice knows: {row.friendName}")
    print("\n")


    # --- Example 3: Filtering Data (People older than 26) ---
    print("--- Query 3: People older than 26 (Filtering) ---")
    query3 = """
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?name ?age
    WHERE {
        ?person foaf:name ?name .
        ?person foaf:age ?age .
        FILTER (?age > 26)
    }
    """
    
    results3 = g.query(query3)
    for row in results3:
        print(f"Name: {row.name} | Age: {row.age}")
    print("\n")

if __name__ == "__main__":
    main()
