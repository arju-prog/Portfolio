// ─────────────────────────────────────────────────────────────
//  Relics — props built in Blender (blender/props/<id>.py) that become
//  public/props/<id>.glb (3D, used in the Armory carousel) and
//  public/props/<id>.png (sprite: dock icons, cursors, click effects, stickers).
// ─────────────────────────────────────────────────────────────

export type Relic = {
  id: string;
  name: string;
  jp: string;
  owner: string; // character id from collection.ts, or '' for extras
  lore: string;
};

export const relics: Relic[] = [
  { id: 'golden_headband', name: 'Golden Headband', jp: '金箍', owner: 'wukong', lore: 'The Great Sage’s golden fillet, crowned with pheasant plumes.' },
  { id: 'jingu_bang', name: 'Ruyi Jingu Bang', jp: '如意金箍棒', owner: 'wukong', lore: 'A staff that grows to any length its master wills.' },
  { id: 'demon_slayer_sword', name: 'Demon-Slayer Sword', jp: '断魔の剣', owner: 'asta', lore: 'A chipped anti-magic greatsword that cuts through any spell.' },
  { id: 'grimoire', name: 'Five-Leaf Grimoire', jp: '五つ葉の魔導書', owner: 'asta', lore: 'The cursed grimoire with a devil in its fifth leaf.' },
  { id: 'straw_hat', name: 'Straw Hat', jp: '麦わら帽子', owner: 'luffy', lore: 'A promise passed from Shanks to the future King of the Pirates.' },
  { id: 'devil_fruit', name: 'Gum-Gum Fruit', jp: 'ゴムゴムの実', owner: 'luffy', lore: 'Swirled, purple, and famously terrible-tasting.' },
  { id: 'kunai', name: 'Kunai', jp: 'クナイ', owner: 'naruto', lore: 'Standard-issue ninja tool of the Hidden Leaf.' },
  { id: 'leaf_headband', name: 'Leaf Headband', jp: '木ノ葉の額当て', owner: 'naruto', lore: 'Proof of a shinobi of Konohagakure.' },
  { id: 'ramen_bowl', name: 'Ichiraku Ramen', jp: '一楽ラーメン', owner: 'naruto', lore: 'Miso chashu, extra narutomaki. Fuel for future Hokage.' },
  { id: 'ofa_glove', name: 'One For All Fist', jp: 'ワン・フォー・オール', owner: 'deku', lore: 'A quirk passed down through generations, crackling with green power.' },
  { id: 'hero_notebook', name: 'Hero Analysis No.13', jp: '将来の為のヒーロー分析', owner: 'deku', lore: 'Singed, soaked, and packed with notes on every hero.' },
  { id: 'leviathan_axe', name: 'Leviathan Axe', jp: 'リヴァイアサンの斧', owner: 'kratos', lore: 'Forged by the Huldra brothers; it always returns to his hand.' },
  { id: 'guardian_shield', name: 'Guardian Shield', jp: '守護の盾', owner: 'kratos', lore: 'Folds away on the forearm, opens into a wall of steel.' },
  { id: 'hidden_blade', name: 'Hidden Blade', jp: 'アサシンブレード', owner: 'ezio', lore: 'Nothing is true; everything is permitted.' },
  { id: 'apple_of_eden', name: 'Apple of Eden', jp: 'エデンの果実', owner: 'ezio', lore: 'A Piece of Eden that bends minds and history.' },
  { id: 'compass', name: 'Drake’s Compass', jp: 'コンパス', owner: 'drake', lore: 'Points to adventure — and occasionally north.' },
  { id: 'drake_ring', name: 'Drake’s Ring', jp: 'ドレイクの指輪', owner: 'drake', lore: 'Sic Parvis Magna — greatness from small beginnings.' },
  { id: 'map_scroll', name: 'Treasure Map', jp: '宝の地図', owner: 'drake', lore: 'X marks the spot. Probably.' },
  { id: 'treasure_chest', name: 'Treasure Chest', jp: '宝箱', owner: 'drake', lore: 'Found by those who follow the compass.' },
];

export const relicsOf = (owner: string) => relics.filter((r) => r.owner === owner);
