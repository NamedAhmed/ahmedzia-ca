import Image from "next/image";
import { links, projects, taste, type Ranked } from "@/content/site";
// Imported, not referenced by path, so a re-rendered image gets a new URL and is never served stale.
import treeRender from "@/public/images/erdtree.jpg";
import styles from "./Erdtree.module.css";

function RankedList({ label, items }: { label: string; items: Ranked[] }) {
  return (
    <div>
      <h3 className={styles.label}>{label}</h3>
      <ul className={styles.ranked}>
        {items.map((item) => (
          <li key={item.title}>
            {item.title}
            <span>{item.note}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// One tall render (blender/build_erdtree.py). The page scrolls down it: leaves, then the
// branches with a project on each, then the trunk with the ranked lists either side.
export default function Erdtree() {
  return (
    <section id="work" className={styles.tree}>
      <Image
        className={styles.render}
        src={treeRender}
        alt="A towering tree of pale gold light in green mist, from its crown of leaves down to its roots"
        sizes="(max-width: 1440px) 100vw, 1440px"
      />
      <div className={styles.fadeTop} />
      <div className={styles.fadeBottom} />

      {projects.map((p) => {
        const place = { top: `${p.card.top}%`, [p.card.side]: `${p.card.inset}%` };
        const inner = (
          <>
            <h2>{p.name}</h2>
            <p>{p.blurb}</p>
          </>
        );
        return (
          <div key={p.name}>
            <span className={styles.dot} style={{ left: `${p.dot.left}%`, top: `${p.dot.top}%` }} />
            {p.href ? (
              <a className={`${styles.pin} ${styles.card}`} style={place} href={p.href}>
                {inner}
              </a>
            ) : (
              <div className={`${styles.pin} ${styles.card}`} style={place}>
                {inner}
              </div>
            )}
          </div>
        );
      })}

      <div id="taste" className={`${styles.pin} ${styles.column}`} style={{ left: "4%", top: "63%" }}>
        <h2 className={styles.heading}>Taste, ranked</h2>
        <RankedList label="Films" items={taste.films} />
        <RankedList label="Books" items={taste.books} />
      </div>

      <div className={`${styles.pin} ${styles.column}`} style={{ right: "4%", top: "66%" }}>
        <RankedList label="Games" items={taste.games} />
        <a className={styles.more} href={links.watchlist}>
          Open the full watchlist
        </a>
      </div>
    </section>
  );
}
