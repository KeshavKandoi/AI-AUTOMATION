export function useMockFor(serviceName: string): boolean {
  const key = `VITE_USE_MOCK_${serviceName.toUpperCase()}`
  const value = import.meta.env[key]
  return value === undefined ? true : value === 'true'
}
