// The temporary password just used to sign in, kept in memory for one use so
// the forced change screen does not ask for it again. Never stored anywhere.
const held = {};

export function holdPassword(kind, password) {
  held[kind] = password;
}

export function takePassword(kind) {
  const password = held[kind] || '';
  delete held[kind];
  return password;
}
