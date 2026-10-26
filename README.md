# Arjun Aggarwal — Portfolio

The portfolio of **Arjun Aggarwal** (AI & Full-Stack Engineer), built with **Next.js**, **Three.js** and **Blender** and styled as a black-and-white manga.

The site is built around **experience**: what I built, how it's architected, and how I work with a team. Anime and game interactions live in an opt-in **Play mode**.

## Opening intro

The first visit in a browser session opens with all 8 characters on stage:
1. They drop in one by one.
2. They dance to a 120 bpm beat, with signature moves rippling across the line: Luffy stretches, Naruto spins, Deku leaps, Asta slashes, Wukong backflips, Kratos stomps, Ezio dive-rolls, Drake shimmies.
3. They pose under your name, then leap out of frame to reveal the site. It lasts about 10 seconds.

How it behaves:
- **Skippable:** Skip button, Esc, Enter, Space, or a click anywhere.
- **Silent by default:** "Sound on" turns on the synthesized beat and effects.
- **Shown once:** it doesn't repeat in the same session. `/?intro` (or "Replay the intro" in the footer) plays it again.
- **Reduced motion:** never shown if the browser asks for reduced motion.
- **Fails safe:** if WebGL or the models are unavailable, it goes straight to the site.
- **No flash:** an inline `<head>` script decides whether to show it before first paint, so neither the page nor the overlay flashes.

The figures are the Blender models in `public/models/`. Rebuild them with `pnpm models`. The choreography is in `src/lib/intro.ts`, and the cast and moves are in `src/data/play/intro.ts`.

## Page

1. **Hero:** my name and current role, three impact metrics, and a live 3D diorama of the current role.
2. **Experience** (the main section). Each work role is a case study with:
   - an impact metrics strip
   - **A — What I built:** the résumé bullets and the stack
   - **B — Architecture:** an interactive system diagram. Select a component to see what I built there; animated edges show the data flow.
   - **C — Leadership & behaviour:** stories in STAR form (Situation, Task, Action, Result).

   Below the case studies sit education and side quests, each with a Blender diorama.
3. **Projects:** compact case studies, each with a collapsible architecture diagram.
4. **Skills:** power levels, achievements, languages and tools.
5. **Contact.**

"Inspect 3D" on any diorama opens one shared 3D dialog with Real, Anime and Manga render styles.

## Play mode (off by default)

The **Play mode** switch in the nav turns the anime and game layer on. The choice is remembered. When it's off, none of the effects, sounds, key bindings or floating widgets are on the page.

| Trigger | What happens |
| --- | --- |
| `J` / `K` | Wukong rides his staff down / up to the next section |
| `L` | Ezio's Leap of Faith back to the top |
| hold `E` | Eagle Vision |
| Nav links | Luffy's arm pulls the page there |
| Axe button | Kratos throws the Leviathan Axe; the page rides to the top and the axe comes back |
| Arsenal (bottom-left) | Equip a power and click anywhere |
| Gold coins | Drake's treasure hunt; the compass points to the nearest coin |
| Armory section | All 21 Blender relics on a 3D ring |

## Scrolling and behaviour rules

- **Native keys are never intercepted:** arrows, Space, PageUp/Down and Home/End always work.
- **Animated scrolls yield to you:** any wheel, touch, pointer or key input cancels them.
- **3D stays out of the way of scrolling:** inline 3D views don't zoom on the mouse wheel, and on touch screens they let vertical swipes scroll the page.
- **Nothing waits to appear:** content is never hidden until a scroll observer fires.
- **One renderer in normal browsing:** a single WebGL view renders unless the 3D dialog or Armory is open.
- **Reduced motion is respected.**

## Code map

```
src/
  data/         profile, experience (+ architecture, STAR), projects; play/ = relics, arsenal, characters
  components/
    experience/ Experience case study, ArchitectureDiagram (SVG), Leadership (STAR)
    projects/   Projects
    sections/   Hero, Nav, Skills, Contact, Footer
    three/      FigureViewer, ModelDialog (shared 3D dialog), Inspect3D
    play/       PlayProvider (all Play state via context), PlayToggle, Arsenal, Interactions, Armory, Treasure…
  lib/          viewer (3D), ring (Armory), fx (canvas effects), journeys, motion (scroll), sfx (Web Audio)
  styles/       base · layout · experience · play
```

Play components get the effects layer, treasure registry and settings from `PlayProvider` through React context. They don't query the DOM for each other or send messages through window events.

## Run it

```bash
pnpm install
pnpm dev          # http://localhost:3000
pnpm kill         # stop this project's Next.js processes
pnpm build && pnpm start
```

## Blender assets

Every 3D object is a Python script run headless in Blender (tested on 5.1). The shared toolkit is `blender/kit.py`.

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/props/<id>.py
# → public/props/<id>.glb (Draco) + <id>.png (ink-outlined sprite)
```

## Edit content

| What | Where |
| --- | --- |
| Roles, impact, architecture, STAR stories | `src/data/experience.ts` |
| Projects + their architecture | `src/data/projects.ts` |
| Name, skills, links | `src/data/profile.ts` |

**To do before publishing:**
- **STAR stories:** they restate your résumé bullets. Add real specifics (numbers, team sizes, outcomes) before publishing.
- **Light Up links:** add the repo and live-demo URLs in `src/data/projects.ts`.
- **Résumé PDF:** `public/resume.pdf` includes your phone number.
