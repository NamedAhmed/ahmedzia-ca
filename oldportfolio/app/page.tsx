import CrtMonitor from "@/components/CrtMonitor";
import Erdtree from "@/components/Erdtree";
import { intro, links } from "@/content/site";

export default function Home() {
  return (
    <main>
      <CrtMonitor />

      <section className="intro">
        <p>{intro}</p>
      </section>

      <Erdtree />

      <footer id="contact" className="footer">
        <span className="footer-name">Ahmed Zia</span>
        <nav aria-label="Contact">
          {links.email && <a href={`mailto:${links.email}`}>{links.email}</a>}
          <a href={links.github}>GitHub</a>
          <a href={links.youtube}>YouTube</a>
        </nav>
        <span className="footer-place">Canada, 2026</span>
      </footer>
    </main>
  );
}
