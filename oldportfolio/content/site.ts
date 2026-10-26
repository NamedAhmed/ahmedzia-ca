// All the words and links on the site live here, so editing content never means touching layout code.

export type Project = {
  name: string;
  blurb: string;
  href?: string;
  // Where the card and its glowing branch marker sit on the tree image, in percent of the image.
  card: { side: "left" | "right"; inset: number; top: number };
  dot: { left: number; top: number };
};

export const projects: Project[] = [
  {
    name: "Homeland Canada",
    blurb:
      "Reviving a family channel with 5.27K subscribers and 380K+ views: a study site, and a pipeline that generates the videos.",
    href: "https://www.youtube.com/@homelandcanada",
    card: { side: "left", inset: 5, top: 19 },
    dot: { left: 27, top: 25.6 },
  },
  {
    name: "Watchlist",
    blurb: "Rank and annotate films, shows and games. Drag-and-drop lists and customisable cards. Live.",
    href: "https://ahmedswatchlist.vercel.app/ahmed",
    card: { side: "right", inset: 6, top: 14 },
    dot: { left: 68, top: 20.2 },
  },
  {
    name: "Music",
    blurb: "An ad-free player for me and a few friends. Private build.",
    card: { side: "left", inset: 2, top: 36.6 },
    dot: { left: 12, top: 35.4 },
  },
  {
    name: "Council",
    blurb: "Ask one question. Several AI models answer, argue with each other, and a chair writes the verdict.",
    card: { side: "right", inset: 2, top: 37.6 },
    dot: { left: 88, top: 36.4 },
  },
  {
    name: "NewsLens",
    blurb: "The same story from left, centre and right, side by side. Break your echo chamber.",
    href: "https://news-app-lime-sigma.vercel.app",
    card: { side: "left", inset: 2, top: 50.4 },
    dot: { left: 10, top: 48.6 },
  },
  {
    name: "Blender films",
    blurb: "A short film about space and a product animation, modelled and cut by me. This tree and monitor too.",
    href: "https://www.youtube.com/@Beep_bop_101",
    card: { side: "right", inset: 2, top: 51.4 },
    dot: { left: 90, top: 47.8 },
  },
];

export type Ranked = { title: string; note: string };

export const taste: { films: Ranked[]; books: Ranked[]; games: Ranked[] } = {
  films: [
    { title: "Dune: Part Two", note: "“Desert propaganda”" },
    { title: "Pride & Prejudice", note: "“I would've folded immediately”" },
    { title: "Blade Runner 2049", note: "“Id live here”" },
  ],
  books: [
    { title: "A Storm of Swords", note: "“I closed this book and stared at my wall.”" },
    { title: "Mistborn: The Final Empire", note: "“This made me like reading.”" },
    { title: "The Merchant of Venice", note: "“Shylock deserved better”" },
  ],
  games: [
    { title: "Elden Ring", note: "“Peck”" },
    { title: "Clair Obscur: Expedition 33", note: "Ranked second" },
    { title: "Ark: Survival Evolved", note: "“This game took too much from me”" },
  ],
};

export const links = {
  watchlist: "https://ahmedswatchlist.vercel.app/ahmed",
  github: "https://github.com/NamedAhmed",
  youtube: "https://www.youtube.com/@homelandcanada",
  // TODO(Ahmed): put your contact email here; the footer hides the email link while this is empty.
  email: "",
};

export const intro =
  "I write code, cut video, model in 3D and start things. I rank everything I watch, read and play, and I have notes.";
