import networkx as nx
from pyvis.network import Network
import json
import os

class MemoryGraph:
    def __init__(self, memory_file="marcus_memory.json"):
        import requests
        self.memory_file = memory_file
        self.graph = nx.Graph()
        self.html_path = os.path.abspath("brain_map.html")
        
        # --- FORCING THE LATEST ENGINE DOWNLOAD ---
        self.js_path = os.path.abspath("3d-force-graph-latest.js") # Changed name to force re-download
        if not os.path.exists(self.js_path):
            print("[ System ] Downloading latest 3D engine... (This only happens once)")
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                # Fetching the absolute newest version without a pinned tag
                res = requests.get("https://unpkg.com/3d-force-graph/dist/3d-force-graph.min.js", headers=headers, timeout=10)
                with open(self.js_path, "w", encoding="utf-8") as f:
                    f.write(res.text)
                print("[ System ] Latest 3D Engine downloaded successfully.")
            except Exception as e:
                print(f"[ System ] Failed to download engine: {e}")
                
        self._load_memory()



    
    def generate_html(self):
        """Builds a Neural Matrix constrained to 7 massively interconnected Super-Clusters."""
        import json
        import networkx as nx
        from networkx.algorithms import community
        
        # 1. INITIAL CLUSTERING
        try:
            communities = list(community.greedy_modularity_communities(self.graph))
        except Exception:
            communities = [set(self.graph.nodes())]
            
        # Convert to sets and sort by size
        communities = sorted([set(c) for c in communities], key=len, reverse=True)
        
        # --- THE HIERARCHICAL 7-SECTOR MERGE ---
        if len(communities) > 7:
            main_sectors = communities[:7]
            small_sectors = communities[7:]
            
            for small_sec in small_sectors:
                best_idx = 0
                max_connections = -1
                
                # Find which of the top 7 this small cluster is most related to
                for idx, main_sec in enumerate(main_sectors):
                    connections = sum(1 for node in small_sec for neighbor in self.graph.neighbors(node) if neighbor in main_sec)
                    if connections > max_connections:
                        max_connections = connections
                        best_idx = idx
                        
                # Merge the small cluster into the most related main cluster
                main_sectors[best_idx].update(small_sec)
                
            communities = main_sectors
        # ---------------------------------------
        
        palette = ["#00f3ff", "#ff00ea", "#39ff14", "#ffc400", "#b026ff", "#ff3366", "#ffffff"]
        
        nodes = []
        cluster_hubs = []
        
        # 2. IDENTIFY SECTORS & BUILD NODES
        for i, comp in enumerate(communities):
            color = palette[i % len(palette)]
            
            # The "Category Name" is mathematically just the most connected node in the super-cluster
            hub_node = max(comp, key=lambda n: self.graph.degree(n))
            cluster_hubs.append(hub_node)
            
            for node in comp:
                is_hub = (node == hub_node)
                is_user = (str(node).lower() in ["user", "nico"])
                
                nodes.append({
                    "id": str(node), 
                    "name": str(node), 
                    "base_val": 18 if is_user else (12 if is_hub else 3),
                    "val": 18 if is_user else (12 if is_hub else 3), 
                    "color": "#ffd700" if is_user else color,
                    "base_color": "#ffd700" if is_user else color,
                    "is_hub": is_hub,
                    "cluster_id": i
                })
                
        # 3. BUILD EDGES
        links = []
        for u, v, d in self.graph.edges(data=True):
            if any(str(u) == n["id"] for n in nodes) and any(str(v) == n["id"] for n in nodes):
                source_color = next((n["color"] for n in nodes if n["id"] == str(u)), "#00e5ff")
                links.append({
                    "source": str(u), 
                    "target": str(v), 
                    "color": source_color 
                })
            
        graph_json = json.dumps({"nodes": nodes, "links": links})

        # 4. THE ENGINE
        html_template = f"""
        <html>
        <head>
          <style> 
            html, body {{ width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; font-family: 'Consolas', monospace; background-color: transparent !important; }} 
            .hud-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; background: linear-gradient(rgba(0, 255, 204, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 204, 0.05) 1px, transparent 1px); background-size: 50px 50px; z-index: 10; box-shadow: inset 0 0 100px rgba(0, 5, 10, 0.9); }}
            .panel {{ position: absolute; color: #00f3ff; font-size: 11px; letter-spacing: 1px; z-index: 11; pointer-events: none; text-shadow: 0 0 5px rgba(0, 243, 255, 0.4); }}
            .top-left {{ top: 20px; left: 20px; border-left: 2px solid #00f3ff; padding-left: 10px; }}
            .bottom-right {{ bottom: 20px; right: 20px; text-align: right; border-right: 2px solid #00f3ff; padding-right: 10px; }}
            #labels-container {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 5; pointer-events: none; }}
            
            .cluster-mist {{
                position: absolute; width: 350px; height: 350px; border-radius: 50%;
                filter: blur(45px); mix-blend-mode: screen; pointer-events: none;
                animation: pulse 4s infinite alternate ease-in-out;
                transition: opacity 0.4s ease, filter 0.4s ease, transform 0.4s ease;
            }}
            @keyframes pulse {{ 0% {{ transform: translate(-50%, -50%) scale(0.85); opacity: 0.1; }} 100% {{ transform: translate(-50%, -50%) scale(1.05); opacity: 0.25; }} }}
            .mist-flash {{ opacity: 0.7 !important; filter: blur(30px) brightness(1.8) !important; transform: translate(-50%, -50%) scale(1.3) !important; }}
            
            /* ULTRA-SLEEK LABELS */
            .cluster-label {{
                position: absolute; background: rgba(3, 6, 10, 0.75); padding: 3px 6px; border: 1px solid;
                font-size: 8px; letter-spacing: 1px; transform: translate(15px, -15px); border-radius: 2px;
            }}
            #3d-graph {{ width: 100%; height: 100%; z-index: 1; }}
          </style>
          <script src="file:///{self.js_path.replace(chr(92), '/')}"></script>
        </head>
        <body>
          <div class="hud-overlay"></div>
          <div class="panel top-left">[ NEURAL MATRIX ]<br>STATUS: ACTIVE<br>NODES: {len(self.graph.nodes())}<br>SECTORS: {len(communities)}</div>
          <div class="panel bottom-right">UPLINK: SECURE<br>SYS.MEM: STABLE<br><span style="color: #ff00ea;">Q-STATE: ALIGNED</span></div>
          <div id="labels-container"></div>
          <div id="3d-graph"></div>
          
          <script>
            function bootGraph() {{
                try {{
                    const gData = {graph_json};
                    const elem = document.getElementById('3d-graph');
                    const labelContainer = document.getElementById('labels-container');
                    
                    const Graph = ForceGraph3D()(elem).graphData(gData);
                    Graph.width(elem.clientWidth); Graph.height(elem.clientHeight);
                    window.addEventListener('resize', () => {{ Graph.width(elem.clientWidth); Graph.height(elem.clientHeight); }});
                    
                    try {{ Graph.backgroundColor('rgba(0,0,0,0)'); }} catch(e) {{}}
                    try {{ Graph.showNavInfo(false); }} catch(e) {{}}
                    
                    const brighten = (hex) => {{
                        if (!hex) return '#ffffff';
                        let r = parseInt(hex.substring(1, 3), 16), g = parseInt(hex.substring(3, 5), 16), b = parseInt(hex.substring(5, 7), 16);
                        r = Math.min(255, Math.floor(r + (255 - r) * 0.6)); g = Math.min(255, Math.floor(g + (255 - g) * 0.6)); b = Math.min(255, Math.floor(b + (255 - b) * 0.6));
                        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
                    }};
                    
                    // --- RESTORED EDGES & ACTIVE DATA STREAMS ---
                    Graph.nodeVal(node => node.isFlashing ? node.val * 2.2 : node.val)
                         .nodeResolution(8)
                         .nodeColor(node => node.isFlashing ? brighten(node.color) : node.color)
                         .linkColor(link => link.color + '55') 
                         .linkWidth(0.8) 
                         .linkDirectionalParticles(2) 
                         .linkDirectionalParticleSpeed(0.015) 
                         .linkDirectionalParticleWidth(3.0) 
                         .linkDirectionalParticleColor(link => link.color + 'aa');
                    
                    Graph.d3Force('charge').strength(-40).distanceMax(150);  
                    Graph.d3Force('link').distance(25); 

                    const trackedElements = [];
                    const mistElements = []; 
                    
                    gData.nodes.forEach(n => {{
                        if (n.is_hub) {{
                            const mist = document.createElement('div');
                            mist.className = 'cluster-mist';
                            mist.style.background = `radial-gradient(circle, ${{n.color}} 0%, transparent 60%)`;
                            mist.style.animationDelay = `-${{Math.random() * 4}}s`; 
                            labelContainer.appendChild(mist);
                            trackedElements.push({{ node: n, el: mist, isMist: true }});
                            mistElements.push(mist);
                            
                            // Sleek, minimal label
                            const label = document.createElement('div');
                            label.className = 'cluster-label';
                            label.innerHTML = `[ <b style="color:#fff">${{n.name.toUpperCase()}}</b> ]`;
                            label.style.borderColor = n.color;
                            label.style.color = n.color;
                            label.style.boxShadow = `0 0 10px ${{n.color}}33`;
                            labelContainer.appendChild(label);
                            trackedElements.push({{ node: n, el: label, isMist: false }});
                        }}
                    }});

                    function updateTracking() {{
                        trackedElements.forEach(item => {{
                            if (item.node.x !== undefined) {{
                                const coords = Graph.graph2ScreenCoords(item.node.x, item.node.y, item.node.z);
                                if (coords.x < -200 || coords.x > window.innerWidth + 200 || coords.y < -200) {{
                                    item.el.style.display = 'none';
                                }} else {{
                                    item.el.style.display = 'block';
                                    item.el.style.left = `${{coords.x}}px`; item.el.style.top = `${{coords.y}}px`;
                                }}
                            }}
                        }});
                        requestAnimationFrame(updateTracking);
                    }}
                    requestAnimationFrame(updateTracking);

                    setInterval(() => {{
                        gData.nodes.forEach(n => {{
                            if (Math.random() < 0.015 && !n.is_hub) {{ 
                                n.isFlashing = true;
                                setTimeout(() => n.isFlashing = false, 1000); 
                            }}
                        }});
                        if (mistElements.length > 0 && Math.random() < 0.35) {{
                            const targetMist = mistElements[Math.floor(Math.random() * mistElements.length)];
                            targetMist.classList.add('mist-flash');
                            setTimeout(() => targetMist.classList.remove('mist-flash'), 1000);
                        }}
                        try {{ Graph.nodeColor(Graph.nodeColor()); Graph.nodeVal(Graph.nodeVal()); }} catch(e) {{}}
                    }}, 400);

                    setTimeout(() => {{ try {{ Graph.zoomToFit(800, 150); }} catch(e) {{}} }}, 1000);

                }} catch (error) {{
                    document.body.innerHTML = `<div style="color:#ff5555; padding: 20px;">[FATAL ERROR] ${{error.message}}</div>`;
                }}
            }}
            window.addEventListener('load', bootGraph);
          </script>
        </body>
        </html>
        """
        
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        return self.html_path

    def _save_memory(self):
        """Saves graph data to a local JSON file so Marcus doesn't forget on reboot."""
        data = nx.node_link_data(self.graph)
        with open(self.memory_file, 'w') as f:
            json.dump(data, f)

    def _load_memory(self):
        """Loads memory on startup."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                self.graph = nx.node_link_graph(data)
            except Exception as e:
                print(f"[ Memory Load Error ]: {e}")
        
        # Generate the initial HTML file on boot
        self.generate_html()



    def remember(self, triples_list):
        """Adds multiple interconnected memories to the graph."""
        for subject, relation, obj in triples_list:
            # Clean up the formatting for visual consistency
            s = str(subject).strip().title()
            r = str(relation).strip().lower()
            o = str(obj).strip().title()
            
            # Add nodes and edges
            self.graph.add_node(s, label=s, title=s, color="#00ffcc")
            self.graph.add_node(o, label=o, title=o, color="#0088ff")
            self.graph.add_edge(s, o, label=r, color="#444444")
            
        self._save_memory()
        self.generate_html()

    def retrieve_context(self, user_query):
        """
        SCALABLE RAG: Scans the graph and only returns facts relevant to the user's query.
        Handles 10,000+ edges instantly in O(E) time.
        """
        if len(self.graph.edges) == 0:
            return "No specific memories stored yet."
            
        # 1. Extract important keywords from the query
        stop_words = {"what", "when", "where", "who", "why", "how", "is", "are", "do", "does", "the", "a", "an", "of", "to", "in", "about"}
        query_words = set()
        
        for word in user_query.lower().replace('?', '').split():
            if word in {"i", "my", "me", "mine"}: 
                query_words.add("user") # Map self-references to the core node
            elif word not in stop_words: 
                query_words.add(word)

        # 2. Search the graph for relevant edges
        relevant_facts = []
        for n1, n2, edge_data in self.graph.edges(data=True):
            relation = edge_data.get('label', '')
            fact_string = f"{n1} {relation} {n2}"
            
            # If any important word from the query matches the subject, relation, or object
            if any(qw in fact_string.lower() for qw in query_words):
                relevant_facts.append(f"- {fact_string}")
                
                # SCALABILITY CAP: Stop after 40 facts to protect the LLM context window
                if len(relevant_facts) >= 40: 
                    break 

        if not relevant_facts:
            return "No relevant facts found for this specific query."
            
        return "\n".join(relevant_facts)
    
    def prune_target(self, target_concept):
        """Surgically removes a target concept, sweeps orphans, and rebuilds the HTML matrix."""
        import json
        import networkx as nx
        
        target_lower = target_concept.lower().strip()
        
        # Protect core logic nodes
        if target_lower in ["user", "nico"]:
            return 0
            
        nodes_to_remove = [n for n in self.graph.nodes() if target_lower in str(n).lower()]
        
        if nodes_to_remove:
            self.graph.remove_nodes_from(nodes_to_remove)
            
            # --- THE ORPHAN SWEEPER ---
            isolates = list(nx.isolates(self.graph))
            isolates = [n for n in isolates if str(n).lower() not in ["user", "nico"]]
            
            if isolates:
                self.graph.remove_nodes_from(isolates)
                print(f"[ Memory Sweeper ] Cleaned up {len(isolates)} orphaned data fragments.")
            
            # Save to JSON
            data = nx.node_link_data(self.graph)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
            # THE CRITICAL FIX: Rebuild the visual HTML file before returning!
            self.generate_html()
            
            return len(nodes_to_remove) + len(isolates)
            
        return 0