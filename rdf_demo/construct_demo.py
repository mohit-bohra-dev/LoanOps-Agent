import rdflib

def main():
    print("1. Loading the Original RDF Graph...")
    g_original = rdflib.Graph()
    
    rdf_data = """
    @prefix ex: <http://example.org/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .

    ex:Alice foaf:name "Alice" ;
             foaf:knows ex:Bob .

    ex:Bob foaf:name "Bob" ;
           foaf:knows ex:Alice, ex:Charlie .

    ex:Charlie foaf:name "Charlie" ;
               foaf:knows ex:Bob .
    """
    g_original.parse(data=rdf_data, format="turtle")
    
    print(f"Original graph has {len(g_original)} statements.\n")

    # 2. Define the CONSTRUCT query
    # We want to create a brand NEW relationship 'ex:friendOfAFriend'
    # between two people if they are connected through a mutual friend.
    print("2. Running CONSTRUCT SPARQL Query...")
    construct_query = """
    PREFIX ex: <http://example.org/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    CONSTRUCT {
        ?person1 ex:friendOfAFriend ?person3 .
    }
    WHERE {
        ?person1 foaf:knows ?person2 .
        ?person2 foaf:knows ?person3 .
        
        # We add a FILTER so we don't accidentally deduce 
        # that Alice is a friend-of-a-friend of herself!
        FILTER (?person1 != ?person3)
    }
    """
    
    # 3. Execute the query
    # A CONSTRUCT query returns a completely new rdflib.Graph object!
    g_new = g_original.query(construct_query)
    
    print(f"The CONSTRUCT query generated a NEW graph with {len(g_new)} statements.\n")

    # 4. Let's look at the new graph
    print("3. Contents of the NEW graph:")
    # We serialize the new graph to Turtle format so we can read it easily
    print(g_new.serialize(format="turtle"))

    # 5. (Optional) We can combine the new graph with our original graph!
    print("4. Merging the new 'friendOfAFriend' knowledge back into the original graph...")
    g_original += g_new
    print(f"Original graph now has {len(g_original)} statements!")

    # 6. Visualizing the final merged graph!
    print("5. Generating Visualization...")
    from pyvis.network import Network
    import os, webbrowser
    
    net = Network(height='750px', width='100%', directed=True)
    
    def simplify_uri(uri):
        s = str(uri)
        if "http://example.org/" in s: return s.replace("http://example.org/", "ex:")
        if "http://xmlns.com/foaf/0.1/" in s: return s.replace("http://xmlns.com/foaf/0.1/", "foaf:")
        return s

    for subj, pred, obj in g_original:
        s_label = simplify_uri(subj)
        p_label = simplify_uri(pred)
        o_label = simplify_uri(obj)

        is_entity = "ex:" in s_label
        net.add_node(s_label, label=s_label, shape="dot" if is_entity else "box", color="#4CAF50" if is_entity else "#2196F3")
        
        is_obj_entity = "ex:" in o_label
        net.add_node(o_label, label=o_label, shape="dot" if is_obj_entity else "box", color="#4CAF50" if is_obj_entity else "#FF9800")
        
        # Color the newly constructed edge differently to make it stand out!
        edge_color = "#E91E63" if "friendOfAFriend" in p_label else "#97C2FC"
        net.add_edge(s_label, o_label, label=p_label, title=p_label, color=edge_color)

    net.toggle_physics(True)
    output_file = "construct_visualization.html"
    net.save_graph(output_file)
    
    file_path = os.path.abspath(output_file)
    print(f"\nVisualization saved to: {file_path}")
    try:
        webbrowser.open(f"file://{file_path}")
    except:
        pass

if __name__ == "__main__":
    main()
