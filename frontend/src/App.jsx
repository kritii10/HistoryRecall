import { NavLink, Route, Routes } from "react-router-dom";
import { GraphPage } from "./pages/GraphPage";
import { HomePage } from "./pages/HomePage";
import { TimelinePage } from "./pages/TimelinePage";

const links = [
  { to: "/", label: "Search" },
  { to: "/timeline", label: "Timeline" },
  { to: "/graph", label: "Graph" }
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="sidebar-badge">Live Memory Workspace</div>
          <p className="eyebrow">Personal Memory Intelligence</p>
          <h1>Personal Memory Intelligence</h1>
          <p className="intro">
            Search your browsing memory, follow topic growth, and see how ideas connect.
          </p>
        </div>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <p className="eyebrow">Workspace Lens</p>
          <p className="sidebar-note">
            Blue-black memory cockpit for semantic recall, timeline tracing, and connected browsing context.
          </p>
        </div>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/graph" element={<GraphPage />} />
        </Routes>
      </main>
    </div>
  );
}
