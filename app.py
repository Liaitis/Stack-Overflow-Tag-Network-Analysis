from flask import Flask, render_template, request, jsonify
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import community
import os
import time
from collections import defaultdict
from matplotlib.colors import Normalize  
app = Flask(__name__, static_url_path='/static', static_folder='static')

with open(r'C:\Users\sreekutty\OneDrive\Desktop\Project_SMA\community_data.pkl', 'rb') as f:
    G, node_attributes, nodes_df = pickle.load(f)
    
with open(r"C:\Users\sreekutty\OneDrive\Desktop\Project_SMA\partition.pkl", "rb") as f:
    partition = pickle.load(f)

def get_top_recommendations(G, target_node, num_recommendations=10):
    def jaccard_similarity(node1, node2):
        neighbors1 = set(G.neighbors(node1))
        neighbors2 = set(G.neighbors(node2))
        common_neighbors = neighbors1.intersection(neighbors2)
        if len(common_neighbors) == 0:
            return 0.0
        return len(common_neighbors) / (len(neighbors1) + len(neighbors2) - len(common_neighbors))

    # Calculate Jaccard similarities between the target node and all other nodes
    similarities = [(node, jaccard_similarity(target_node, node)) for node in G.nodes() if node != target_node]
    sorted_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)
    top_recommendations = [node for node, similarity in sorted_similarities[:num_recommendations]]

    return top_recommendations

def visualize_and_get_community_info(G, node_attributes, target_community_id, nodes_df, node_alpha=0.9):
    node_attributes = {}
    for _, row in nodes_df.iterrows():
        node_name = row['name']
        if node_name in G.nodes:
            # Convert the inner tuple to a dictionary
            node_attributes[node_name] = {
                'group': row['group'],
                'nodesize': row['nodesize']
            }
        else:
            print(f"Node '{node_name}' not found in the graph.")

    nx.set_node_attributes(G, node_attributes)
    partition = node_attributes
    community_groups = defaultdict(list)
    for node, attributes in partition.items():
        group = attributes['group']
        community_groups[group].append(node)


    degree_centrality = nx.degree_centrality(G)
    if target_community_id in community_groups:
        nodes_in_target_community = community_groups[target_community_id]
    else:
        print(f"Community {target_community_id} not found or empty.")
        return None

    sorted_nodes = sorted(nodes_in_target_community, key=lambda x: degree_centrality[x], reverse=True)
    community_size = len(sorted_nodes)  
    degree_centrality_values = [degree_centrality[node] for node in sorted_nodes]

    community_info = {
        "Community ID": target_community_id,
        "Total Members": community_size,
        "Members (sorted by Degree Centrality)": [
            {"Member": member, "Degree Centrality": centrality}
            for member, centrality in zip(sorted_nodes, degree_centrality_values)
        ]
    }

    community_subgraph = G.subgraph(nodes_in_target_community)
    node_sizes = [25 * nodes_df[nodes_df['name'] == node]['nodesize'].values[0] for node in nodes_in_target_community]
    colormap = plt.get_cmap('Pastel1') 
    norm = Normalize(vmin=min(degree_centrality.values()), vmax=max(degree_centrality.values()))
    node_colors = [colormap(norm(degree_centrality[node])) for node in community_subgraph.nodes()]
    node_colors_with_alpha = [(r, g, b, node_alpha) for r, g, b, _ in node_colors]
    plt.figure(figsize=(16, 6))
    pos = nx.kamada_kawai_layout(community_subgraph)  
    nx.draw(community_subgraph, pos, with_labels=True, node_size=node_sizes, node_color=node_colors_with_alpha, font_size=10, cmap=colormap)
    plt.title(f"Community {target_community_id} Visualization")
    sm = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, orientation="vertical")
    cbar.set_label('Degree Centrality')
    plt.savefig(r"C:\Users\sreekutty\OneDrive\Desktop\Project_SMA\static\community1.png")
    plt.show()

    return community_info


    
@app.route('/visualize', methods=['POST'])
def visualize_community():
    target_community_id = int(request.form.get('community_id'))
    available_community_ids = list(sorted(set(node_data['group'] for node_data in partition.values())))
    community_info = visualize_and_get_community_info(G, node_attributes, target_community_id, nodes_df)

    if community_info:
        formatted_result = {
            'Community ID': community_info['Community ID'],
            'Total Members':community_info['Total Members'],
            'Community Members': [
                {
                    'Member': member_info['Member'],
                    'Degree Centrality': member_info['Degree Centrality']
                }
                for member_info in community_info['Members (sorted by Degree Centrality)']
            ]
        }
        timestamp = int(time.time())

        return render_template("Community.html", available_community_ids=available_community_ids, result=formatted_result, timestamp=timestamp)
    else:
        return jsonify({'error': f"Community {target_community_id} not found or empty."})


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detection', methods=['GET', 'POST'])
def Recommendation():
    if request.method == 'POST':
        node_name = request.form['node_name']
        similar_nodes = get_top_recommendations(G, node_name, num_recommendations=10)
    else:
        node_name = ''
        similar_nodes = []

    return render_template('Recommendation.html', node_name=node_name, similar_nodes=similar_nodes)

@app.route('/community', methods=['GET', 'POST'])
def Community():
    available_community_ids = list(sorted(set(node_data['group'] for node_data in partition.values())))
    return render_template('Community.html', available_community_ids=available_community_ids)


if __name__ == "__main__":
    static_dir = os.path.join(os.getcwd(), "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    app.run(debug=True)
