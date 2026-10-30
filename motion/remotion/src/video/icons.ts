// أيقونات Material Symbols Rounded المستخدمة في الفيديو (اسم -> codepoint).
export const ICONS: Record<string, number> = {
  "back_hand": 0xe764,
  "bolt": 0xea0b,
  "campaign": 0xef49,
  "checklist": 0xe6b1,
  "door_front": 0xeffd,
  "favorite": 0xe87e,
  "flag": 0xf0c6,
  "folded_hands": 0xf5ed,
  "forum": 0xe8af,
  "group_off": 0xe747,
  "groups": 0xf233,
  "handshake": 0xebcb,
  "help": 0xe8fd,
  "landscape": 0xe564,
  "place": 0xf1db,
  "menu_book": 0xea19,
  "mosque": 0xeab2,
  "school": 0xe80c,
  "search": 0xef7a,
  "shield": 0xe9e0,
  "star": 0xf09a,
  "swords": 0xf889,
  "volunteer_activism": 0xea70,
};

export const iconGlyph = (name?: string): string => {
  if (!name) return '';
  const cp = ICONS[name];
  return typeof cp === 'number' ? String.fromCodePoint(cp) : '';
};
