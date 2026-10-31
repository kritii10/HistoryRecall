import { useEffect, useState } from "react";
import { fetchTimeline } from "../lib/api";

export function TimelinePage() {
  const [points, setPoints] = useState([]);
  const maxCount = Math.max(...points.map((point) => point.count), 1);

  useEffect(() => {
    let ignore = false;

    fetchTimeline().then((result) => {
      if (!ignore) {
        setPoints(result.points);
      }
    });

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <section className="dashboard-page">
      <div className="panel hero hero-primary">
        <div className="hero-copy">
          <p className="eyebrow">Learning Timeline</p>
          <h2>Track what topics showed up over time</h2>
          <p className="hero-text">
            Follow the rhythm of your browsing memory and see which interests are building momentum.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="timeline-list">
          {points.map((point, index) => (
            <div key={`${point.month}-${point.topic}-${index}`} className="timeline-item">
              <div className="timeline-dot" />
              <div className="timeline-content">
                <p className="timeline-month">{point.month}</p>
                <h3>{point.topic}</h3>
                <p className="muted">{point.count} memory captured</p>
                <div className="timeline-bar-track">
                  <div
                    className="timeline-bar-fill"
                    style={{ width: `${(point.count / maxCount) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
