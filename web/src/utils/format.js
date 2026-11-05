// Display helpers shared by the admin and user views.

// The API sends UTC timestamps without an offset; read them as UTC, not local time.
export function toDate(value) {
  if (typeof value === 'string' && /T\d{2}:\d{2}/.test(value) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(value)) {
    return new Date(`${value}Z`);
  }
  return new Date(value);
}

export function relativeTime(value) {
  if (!value) return 'Never';
  const date = toDate(value);
  const minutes = Math.floor((Date.now() - date) / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}d ago`;
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export function dateTime(value) {
  if (!value) return '—';
  return toDate(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function shortDate(value) {
  if (!value) return '—';
  // Plain dates (birthdays) have no time zone; show them as written.
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  return toDate(value).toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric', ...(dateOnly && { timeZone: 'UTC' }),
  });
}

export function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : '';
}

export function formatNumber(value) {
  return typeof value === 'number' ? value.toLocaleString() : '—';
}

export function roleBadge(role) {
  if (role === 'root') return 'badge-danger';
  if (role === 'admin') return 'badge-primary';
  return '';
}
