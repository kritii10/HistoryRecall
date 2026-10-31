import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { fetchGraph } from "../lib/api";

export function GraphPage() {
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const svgRef = useRef(null);

  useEffect(() => {
    let ignore = false;

    fetchGraph().then((result) => {
      if (!ignore) {
        setGraph(result);
      }
    });

    return () => {
      ignore = true;
    };
  }, []);

  const nodeLabels = Object.fromEntries(graph.nodes.map((node) => [node.id, node.label]));
  const nodeCounts = graph.nodes.reduce((counts, node) => {
    counts[node.type] = (counts[node.type] || 0) + 1;
    return counts;
  }, {});
  useEffect(() => {
    if (!selectedNodeId && graph.nodes.length) {
      setSelectedNodeId(graph.nodes[0].id);
    }
  }, [graph.nodes, selectedNodeId]);

  const selectedNode = useMemo(
    () => graph.nodes.find((node) => node.id === selectedNodeId) || graph.nodes[0] || null,
    [graph.nodes, selectedNodeId]
  );
  const relatedLinks = useMemo(
    () =>
      graph.links.filter(
        (link) => link.source === selectedNode?.id || link.target === selectedNode?.id
      ),
    [graph.links, selectedNode]
  );

  useEffect(() => {
    if (!svgRef.current || !graph.nodes.length) {
      return;
    }

    const width = 760;
    const height = 420;
    const colorByType = {
      user: "#182218",
      memory: "#7bb661",
      topic: "#f3b33d",
      source: "#4f7ddb"
    };

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const simulationNodes = graph.nodes.map((node) => ({ ...node }));
    const simulationLinks = graph.links.map((link) => ({ ...link }));

    const simulation = d3
      .forceSimulation(simulationNodes)
      .force("link", d3.forceLink(simulationLinks).id((d) => d.id).distance(110))
      .force("charge", d3.forceManyBody().strength(-260))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(34));

    const link = svg
      .append("g")
      .attr("stroke", "#b8c2b1")
      .attr("stroke-opacity", 0.8)
      .selectAll("line")
      .data(simulationLinks)
      .join("line")
      .attr("stroke-width", 1.8);

    const linkLabel = svg
      .append("g")
      .selectAll("text")
      .data(simulationLinks)
      .join("text")
      .attr("font-size", 11)
      .attr("fill", "#60705d")
      .attr("text-anchor", "middle")
      .text((d) => d.label);

    const node = svg
      .append("g")
      .selectAll("g")
      .data(simulationNodes)
      .join("g")
      .style("cursor", "grab")
      .on("click", (_event, clickedNode) => {
        setSelectedNodeId(clickedNode.id);
      })
      .call(
        d3
          .drag()
          .on("start", (event, draggedNode) => {
            if (!event.active) {
              simulation.alphaTarget(0.3).restart();
            }
            draggedNode.fx = draggedNode.x;
            draggedNode.fy = draggedNode.y;
          })
          .on("drag", (event, draggedNode) => {
            draggedNode.fx = event.x;
            draggedNode.fy = event.y;
          })
          .on("end", (event, draggedNode) => {
            if (!event.active) {
              simulation.alphaTarget(0);
            }
            draggedNode.fx = null;
            draggedNode.fy = null;
          })
      );

    node
      .append("circle")
      .attr("r", (d) => (d.type === "user" ? 24 : 19))
      .attr("fill", (d) => colorByType[d.type] || "#999999")
      .attr("stroke", "#fffdf8")
      .attr("stroke-width", 3);

    node
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", 4)
      .attr("font-size", 10)
      .attr("font-weight", 700)
      .attr("fill", "#fffdf8")
      .text((d) => d.label.slice(0, 12));

    node.append("title").text((d) => `${d.label} (${d.type})`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      linkLabel
        .attr("x", (d) => (d.source.x + d.target.x) / 2)
        .attr("y", (d) => (d.source.y + d.target.y) / 2 - 6);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [graph]);

  return (
    <section className="dashboard-page">
      <div className="panel hero hero-primary">
        <div className="hero-copy">
          <p className="eyebrow">Knowledge Graph</p>
          <h2>See how pages, topics, and sources connect</h2>
          <p className="hero-text">
            This graph turns browsing memories into a connected workspace so you can inspect
            relationships instead of isolated links.
          </p>
        </div>
        <div className="graph-summary">
          {Object.entries(nodeCounts).map(([type, count]) => (
            <div key={type} className="summary-pill">
              <strong>{count}</strong>
              <span>{type}</span>
            </div>
          ))}
        </div>
      </div>

      <section className="panel">
        <div className="graph-canvas-shell">
          <svg ref={svgRef} className="graph-canvas" role="img" aria-label="Knowledge graph" />
        </div>

        <div className="graph-layout">
          <div>
            <h3>Nodes</h3>
            <div className="mini-list">
              {graph.nodes.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  className={selectedNode?.id === node.id ? "list-item node-button active" : "list-item node-button"}
                  onClick={() => setSelectedNodeId(node.id)}
                >
                  <strong>{node.label}</strong>
                  <span>{node.type}</span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <h3>Links</h3>
            <div className="mini-list">
              {graph.links.map((link, index) => (
                <div key={`${link.source}-${link.target}-${index}`} className="list-item">
                  <strong>{link.label}</strong>
                  <span>{`${nodeLabels[link.source] || link.source} -> ${nodeLabels[link.target] || link.target}`}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {selectedNode ? (
          <div className="graph-focus-card">
            <p className="eyebrow">Focus</p>
            <h3>{selectedNode.label}</h3>
            <p className="muted">Type: {selectedNode.type}</p>
            <div className="mini-list">
              {relatedLinks.map((link, index) => (
                <div key={`${link.source}-${link.target}-${index}-focus`} className="list-item">
                  <strong>{link.label}</strong>
                  <span>{`${nodeLabels[link.source] || link.source} -> ${nodeLabels[link.target] || link.target}`}</span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </section>
  );
}
