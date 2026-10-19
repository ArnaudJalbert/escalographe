import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

class ResizeObserverMock { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', ResizeObserverMock)

afterEach(() => { cleanup(); vi.restoreAllMocks() })
vi.mock('../src/components/AtlasMap', () => ({
  AtlasMap: ({ escalators }: { escalators: unknown[] }) => <div data-testid="mock-map">Map: {escalators.length} markers</div>,
  DetailMap: () => <div data-testid="mock-detail-map" />,
  useEscalatorDetail: () => ({ data: undefined, isLoading: true }),
}))
