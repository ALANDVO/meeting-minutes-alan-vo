export function capitalizeStatus(status: string): string {
  return status.replace(/_/g, ' ').split(' ').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ')
}
