import type { Metadata } from "next";
import { Cormorant_Garamond, Instrument_Sans, VT323 } from "next/font/google";
import "./globals.css";

const terminal = VT323({ variable: "--font-terminal", weight: "400", subsets: ["latin"] });
const display = Cormorant_Garamond({ variable: "--font-display", weight: ["400", "500"], subsets: ["latin"] });
const body = Instrument_Sans({ variable: "--font-body", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Ahmed Zia",
  description: "Student in Canada who writes code, cuts video, models in 3D and starts things.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${terminal.variable} ${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
