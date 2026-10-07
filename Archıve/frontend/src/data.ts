import {
  Bot,
  Clapperboard,
  Gamepad2,
  Images,
  Landmark,
  Sparkles,
} from "lucide-react";
import type { ProjectMode, VideoProject } from "./types";

export const projectModes: ProjectMode[] = [
  {
    id: "ai-photos",
    title: "Storyteller with AI photos",
    description:
      "Turn an original idea into a narrated visual story with a consistent AI art direction.",
    engine: "Storyteller engine",
    available: true,
    badge: "Popular",
    accent: "coral",
    Icon: Sparkles,
    promptPlaceholder:
      "A night-shift taxi driver picks up a passenger from a town that disappeared 30 years ago…",
    examples: ["Mystery story", "Life lesson", "Animated animal tale"],
  },
  {
    id: "reddit",
    title: "Storyteller with Reddit video",
    description:
      "Pair a punchy story with gameplay footage, animated captions, and word-perfect narration.",
    engine: "Storyteller engine",
    available: true,
    badge: "Fastest",
    accent: "lime",
    Icon: Gamepad2,
    promptPlaceholder:
      "Paste a Reddit post, confession, or write the story you want narrated…",
    examples: ["AITA story", "Confession", "Plot twist"],
  },
  {
    id: "real-images",
    title: "Storyteller with real images",
    description:
      "Build a credible story around authentic, source-aware images and documentary framing.",
    engine: "Research engine",
    available: true,
    accent: "blue",
    Icon: Images,
    promptPlaceholder:
      "The community that rebuilt its town after the 1999 earthquake…",
    examples: ["True story", "Biography", "News context"],
  },
  {
    id: "documentary",
    title: "Historical documentary",
    description:
      "Research an event, find archival visuals, and explain what happened with citations.",
    engine: "Research engine",
    available: true,
    badge: "Best match",
    accent: "gold",
    Icon: Landmark,
    promptPlaceholder:
      "How Turkey's 2001 financial crisis changed the country's economy…",
    examples: ["Historic event", "Rise & fall", "Untold history"],
  },
  {
    id: "stock-explainer",
    title: "Stock footage explainer",
    description:
      "Make fast educational shorts with licensed stock visuals, voiceover, and clear captions.",
    engine: "Hybrid engine",
    available: false,
    badge: "Coming soon",
    accent: "violet",
    Icon: Clapperboard,
    promptPlaceholder:
      "Why deep-sea cables carry almost all international internet traffic…",
    examples: ["How it works", "Top 5", "Science fact"],
  },
  {
    id: "avatar",
    title: "AI avatar presenter",
    description:
      "Let a consistent virtual host deliver explainers, tutorials, or branded updates.",
    engine: "Presenter engine",
    available: false,
    badge: "Coming soon",
    accent: "mint",
    Icon: Bot,
    promptPlaceholder:
      "Three small changes that make your morning routine more focused…",
    examples: ["Tutorial", "Product demo", "Daily update"],
  },
];

export const starterVideos: VideoProject[] = [
  {
    id: "demo-1",
    title: "The library that only opens at midnight",
    modeId: "ai-photos",
    mode: "AI photo story",
    date: "Today, 10:42",
    duration: "00:42",
    status: "Ready",
    stage: "Ready to download",
    accent: "coral",
  },
  {
    id: "demo-2",
    title: "Why Roman roads lasted for centuries",
    modeId: "documentary",
    mode: "Historical documentary",
    date: "Yesterday",
    duration: "00:58",
    status: "Ready",
    stage: "Ready to download",
    accent: "gold",
  },
  {
    id: "demo-3",
    title: "My roommate had one impossible rule",
    modeId: "reddit",
    mode: "Reddit story",
    date: "Jul 26",
    duration: "01:04",
    status: "Draft",
    stage: "Ready to generate",
    accent: "lime",
  },
];
