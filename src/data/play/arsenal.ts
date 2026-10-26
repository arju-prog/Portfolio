// Equippable items. `id` is the relic whose Blender sprite is used as the icon + cursor.

export type WeaponId =
  | 'golden_headband'
  | 'demon_slayer_sword'
  | 'kunai'
  | 'ofa_glove'
  | 'straw_hat'
  | 'leviathan_axe'
  | 'hidden_blade'
  | 'compass';

export type Weapon = { id: WeaponId; owner: string; name: string; power: string; hint: string };

export const weapons: Weapon[] = [
  { id: 'golden_headband', owner: 'wukong', name: 'Golden Headband', power: 'Jingu Bang Slam', hint: 'Click anywhere — the staff slams down from the sky' },
  { id: 'demon_slayer_sword', owner: 'asta', name: 'Demon-Slayer Sword', power: 'Anti-Magic Slash', hint: 'Click or drag to slash' },
  { id: 'kunai', owner: 'naruto', name: 'Kunai', power: 'Rasengan', hint: 'Hold to charge a Rasengan, release to blast' },
  { id: 'ofa_glove', owner: 'deku', name: 'One For All', power: 'Detroit Smash', hint: 'Click to smash' },
  { id: 'straw_hat', owner: 'luffy', name: 'Straw Hat', power: 'Gum-Gum Pistol', hint: 'Click — a stretchy punch flies in' },
  { id: 'leviathan_axe', owner: 'kratos', name: 'Leviathan Axe', power: 'Frost Throw', hint: 'Click to throw — it always comes back' },
  { id: 'hidden_blade', owner: 'ezio', name: 'Hidden Blade', power: 'Strike · Eagle Vision', hint: 'Click to strike · hold for Eagle Vision' },
  { id: 'compass', owner: 'drake', name: 'Drake’s Compass', power: 'Treasure Hunt', hint: 'Follow the needle, click to dig for treasure' },
];

export const weaponOf = (owner: string) => weapons.find((w) => w.owner === owner);
