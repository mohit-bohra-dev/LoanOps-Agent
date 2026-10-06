import rdflib
from pyvis.network import Network
import os
import webbrowser

def main():
    print("Loading RDF Graph...")
    g = rdflib.Graph()
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
    g.parse(data=rdf_data, format="turtle")

    print("Building interactive visualization...")
    # Create an interactive network graph
    net = Network(height='750px', width='100%', directed=True)

    # Helper function to make long URIs readable in the graph
    def simplify_uri(uri):
        s = str(uri)
        if "http://example.org/" in s:
            return s.replace("http://example.org/", "ex:")
        if "http://xmlns.com/foaf/0.1/" in s:
            return s.replace("http://xmlns.com/foaf/0.1/", "foaf:")
        return s

    # Add nodes and edges from our RDF triples
    for subj, pred, obj in g:
        s_label = simplify_uri(subj)
        p_label = simplify_uri(pred)
        o_label = simplify_uri(obj)

        # Style subjects (usually entities like ex:Alice) as green dots
        is_entity = "ex:" in s_label
        net.add_node(s_label, label=s_label, shape="dot" if is_entity else "box", 
                     color="#4CAF50" if is_entity else "#2196F3")
        
        # Style objects (could be entities or literal values like "30")
        is_obj_entity = "ex:" in o_label
        net.add_node(o_label, label=o_label, shape="dot" if is_obj_entity else "box", 
                     color="#4CAF50" if is_obj_entity else "#FF9800")
        
        # Add the connection (Predicate)
        net.add_edge(s_label, o_label, label=p_label, title=p_label)

    # Physics settings to make the graph arrange itself nicely
    net.toggle_physics(True)

    # Save to HTML file
    output_file = "graph_visualization.html"
    net.save_graph(output_file)
    
    file_path = os.path.abspath(output_file)
    print(f"\nVisualization saved to: {file_path}")
    
    # Attempt to open it automatically in the default web browser
    try:
        webbrowser.open(f"file://{file_path}")
        print("Opening in your web browser...")
    except:
        print("Please open this file in your web browser to view the graph.")

if __name__ == "__main__":
    main()
