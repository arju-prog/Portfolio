// The opening cast: who drops in (in order), their signature dance move and its sound-effect text.
// Models are the full figures built by `pnpm models` (public/models/<id>.glb).

export type Move = 'stretch' | 'spin' | 'leap' | 'slash' | 'flip' | 'stomp' | 'dive' | 'wave';

export type CastMember = { id: string; short: string; move: Move; sfx: string; color: string };

export const cast: CastMember[] = [
  { id: 'luffy', short: 'Luffy', move: 'stretch', sfx: 'ゴムゴム!', color: '#d7262b' },
  { id: 'naruto', short: 'Naruto', move: 'spin', sfx: '影分身!', color: '#f28c1b' },
  { id: 'deku', short: 'Deku', move: 'leap', sfx: 'SMASH!', color: '#3cff2a' },
  { id: 'asta', short: 'Asta', move: 'slash', sfx: 'ズバッ!', color: '#cfc8ac' },
  { id: 'wukong', short: 'Wukong', move: 'flip', sfx: 'ドン!', color: '#e3a92b' },
  { id: 'kratos', short: 'Kratos', move: 'stomp', sfx: 'ドドド', color: '#a3191a' },
  { id: 'ezio', short: 'Ezio', move: 'dive', sfx: 'シュッ', color: '#f0ece3' },
  { id: 'drake', short: 'Drake', move: 'wave', sfx: 'お宝!', color: '#3d6fa8' },
];

/** What the cast says while presenting the site (one bubble, from the centre of the line-up). */
export const welcomeLine = 'Welcome! Come see what Arjun builds →';
