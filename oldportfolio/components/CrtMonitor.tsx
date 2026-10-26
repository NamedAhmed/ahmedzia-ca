import Image from "next/image";
import { projects } from "@/content/site";
import monitorRender from "@/public/images/crt-monitor.webp";
import styles from "./CrtMonitor.module.css";

// The monitor is a Blender render (blender/build_crt.py) with a dark screen.
// The terminal is live HTML laid over the screen opening, so the text stays real and selectable.
export default function CrtMonitor() {
  return (
    <header className={styles.hero}>
      <div className={styles.monitor}>
        <Image
          className={styles.shell}
          src={monitorRender}
          alt=""
          sizes="(max-width: 1000px) 94vw, 1000px"
          preload
        />

        <div className={styles.screen}>
          <span className={styles.ghost} aria-hidden="true">
            Ahmed
          </span>

          <div className={styles.beam}>
            <p className={styles.line}>ahmed@zia:~$ whoami</p>

            <div className={styles.nameWrap}>
              <h1 className={styles.name}>
                Ahmed
                <span className={styles.surname}>
                  zia
                  <span className={styles.cursor} aria-hidden="true" />
                </span>
              </h1>
            </div>

            <p className={`${styles.line} ${styles.listing}`}>ahmed@zia:~$ ls projects/</p>
            <ul className={`${styles.files} ${styles.listing}`}>
              {projects.map((p) => (
                <li key={p.name}>
                  <a href="#work">{p.name.toLowerCase().replace(/ /g, "-")}/</a>
                </li>
              ))}
            </ul>

            <nav className={styles.status} aria-label="Sections">
              <span>AHMED ZIA(1)</span>
              <a href="#work">work</a>
              <a href="#taste">taste</a>
              <a href="#contact">contact</a>
              <span className={styles.place}>student, Canada</span>
            </nav>
          </div>

          {/* effect layers, back to front: static, scanlines, colour mask, rolling bar, glass */}
          <svg className={styles.snow} aria-hidden="true">
            <filter id="crt-noise">
              <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" />
              <feColorMatrix type="saturate" values="0" />
            </filter>
            <rect width="100%" height="100%" filter="url(#crt-noise)" />
          </svg>
          <div className={styles.scanlines} />
          <div className={styles.mask} />
          <div className={styles.roll} />
          <div className={styles.glass} />
        </div>
      </div>
    </header>
  );
}
