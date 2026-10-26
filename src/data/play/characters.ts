// ─────────────────────────────────────────────────────────────
//  The anime & game characters behind the site's interactions
//  (powers, relics, sounds). Their full figures aren't shown; the
//  Blender scripts in blender/characters/ can still build them
//  into public/models/ with `pnpm models`.
// ─────────────────────────────────────────────────────────────

export type Category = 'anime' | 'game';

export type Character = {
  id: string;
  name: string;
  jp: string;
  franchise: string;
  category: Category;
  quote: string;
  bio: string;
  signature: string; // signature move / item
  abilities: string[];
  stats: { power: number; speed: number; technique: number; spirit: number };
  color: string; // primary colour, used for small accents
};

export const characters: Character[] = [
  {
    id: 'luffy',
    name: 'Monkey D. Luffy',
    jp: 'モンキー・D・ルフィ',
    franchise: 'One Piece',
    category: 'anime',
    quote: 'I’m gonna be King of the Pirates!',
    bio: 'Rubber-bodied captain of the Straw Hat Pirates. Never without the straw hat, always hungry, and impossible to stop once he’s decided to protect his friends.',
    signature: 'Gum-Gum Pistol',
    abilities: ['Rubber body', 'Haki', 'Gear Fifth'],
    stats: { power: 95, speed: 88, technique: 70, spirit: 100 },
    color: '#d7262b',
  },
  {
    id: 'naruto',
    name: 'Naruto Uzumaki',
    jp: 'うずまきナルト',
    franchise: 'Naruto',
    category: 'anime',
    quote: 'I never go back on my word — that’s my ninja way!',
    bio: 'The loud, stubborn ninja of the Hidden Leaf who turned loneliness into an unbreakable will and grew from outcast to Hokage.',
    signature: 'Rasengan',
    abilities: ['Shadow Clones', 'Sage Mode', 'Nine-Tails Chakra'],
    stats: { power: 94, speed: 90, technique: 78, spirit: 99 },
    color: '#f28c1b',
  },
  {
    id: 'deku',
    name: 'Izuku Midoriya',
    jp: '緑谷出久',
    franchise: 'My Hero Academia',
    category: 'anime',
    quote: 'Go beyond — Plus Ultra!',
    bio: 'Born quirkless, chosen anyway. Deku inherits One For All and fills notebooks with analysis on his way to becoming the greatest hero.',
    signature: 'One For All: Detroit Smash',
    abilities: ['One For All', 'Full Cowl', 'Blackwhip'],
    stats: { power: 92, speed: 89, technique: 86, spirit: 97 },
    color: '#1f8a5b',
  },
  {
    id: 'asta',
    name: 'Asta',
    jp: 'アスタ',
    franchise: 'Black Clover',
    category: 'anime',
    quote: 'Surpassing my limits, right here, right now!',
    bio: 'A boy born with zero magic in a world run on it. Armed with a five-leaf grimoire and anti-magic swords, he’s aiming for Wizard King.',
    signature: 'Demon-Slayer Sword',
    abilities: ['Anti-Magic', 'Devil Union', 'Ki sense'],
    stats: { power: 90, speed: 84, technique: 72, spirit: 100 },
    color: '#3a3a3a',
  },
  {
    id: 'wukong',
    name: 'The Destined One',
    jp: '天命人',
    franchise: 'Black Myth: Wukong',
    category: 'game',
    quote: 'The journey west begins again.',
    bio: 'A monkey warrior walking the path of the Great Sage, staff in hand, through a world of yaoguai drawn from Journey to the West.',
    signature: 'Jingu Bang Staff',
    abilities: ['Spells & transformations', 'Immobilize', 'Cloud Step'],
    stats: { power: 91, speed: 87, technique: 94, spirit: 88 },
    color: '#c8962e',
  },
  {
    id: 'kratos',
    name: 'Kratos',
    jp: 'クレイトス',
    franchise: 'God of War',
    category: 'game',
    quote: 'Do not be sorry. Be better.',
    bio: 'The Ghost of Sparta, now a father in the realms of Norse myth — learning restraint while carrying the Leviathan Axe.',
    signature: 'Leviathan Axe',
    abilities: ['Spartan Rage', 'Blades of Chaos', 'Runic attacks'],
    stats: { power: 100, speed: 70, technique: 88, spirit: 90 },
    color: '#b3261e',
  },
  {
    id: 'ezio',
    name: 'Ezio Auditore',
    jp: 'エツィオ・アウディトーレ',
    franchise: 'Assassin’s Creed',
    category: 'game',
    quote: 'Nothing is true; everything is permitted.',
    bio: 'A Florentine noble turned Master Assassin. Rooftop runner, hidden-blade expert and mentor of the Brotherhood.',
    signature: 'Hidden Blade',
    abilities: ['Free running', 'Eagle Vision', 'Leap of Faith'],
    stats: { power: 72, speed: 92, technique: 97, spirit: 86 },
    color: '#9c1b1f',
  },
  {
    id: 'drake',
    name: 'Nathan Drake',
    jp: 'ネイサン・ドレイク',
    franchise: 'Uncharted',
    category: 'game',
    quote: 'Sic Parvis Magna — greatness from small beginnings.',
    bio: 'Treasure hunter, climber and wisecracking survivor of every collapsing ruin. Never far from Sir Francis Drake’s ring.',
    signature: 'Drake’s Ring',
    abilities: ['Climbing', 'Puzzle solving', 'Lucky escapes'],
    stats: { power: 68, speed: 84, technique: 85, spirit: 93 },
    color: '#3d6fa8',
  },
];
