// Mirrors the API's password policy (app/models/user_api_model.py) so users
// see problems before submitting. The API remains the authority.
export const PASSWORD_MIN = 12;
export const PASSWORD_MAX = 128;
export const PASSWORD_SYMBOLS = '@#$%^&+=!';

export function passwordProblems(password) {
  const problems = [];
  if (password.length < PASSWORD_MIN) problems.push(`at least ${PASSWORD_MIN} characters`);
  if (password.length > PASSWORD_MAX) problems.push(`at most ${PASSWORD_MAX} characters`);
  if (!/[a-z]/.test(password)) problems.push('a lowercase letter');
  if (!/[A-Z]/.test(password)) problems.push('an uppercase letter');
  if (!/[0-9]/.test(password)) problems.push('a number');
  if (!/[@#$%^&+=!]/.test(password)) problems.push(`a symbol (${PASSWORD_SYMBOLS})`);
  return problems;
}

export function passwordError(password, confirmation) {
  const problems = passwordProblems(password);
  if (problems.length) return `Password needs ${problems.join(', ')}.`;
  if (confirmation !== undefined && confirmation !== password) return 'Passwords do not match.';
  return '';
}

// Only same-app paths may be used as a post-login destination (no open redirects).
export function safeNextPath(next) {
  if (typeof next !== 'string') return null;
  if (!next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return null;
  return next;
}

// Drop empty strings so optional fields are left unset rather than sent as "".
export function withoutEmpty(data) {
  return Object.fromEntries(Object.entries(data).filter(([, value]) => value !== ''));
}
