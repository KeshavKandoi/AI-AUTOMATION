import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/Button'

interface Props { children: ReactNode }
interface State { failed: boolean }

export default class PageErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State { return { failed: true } }

  componentDidCatch(error: Error, _info: ErrorInfo) {
    console.error('Page render failed:', error.name)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div role="alert" className="mx-auto max-w-xl p-8 text-text-primary">
        <h1 className="text-xl font-semibold">This page could not be displayed</h1>
        <p className="mt-2 text-sm text-text-muted">Please reload the page. If the problem continues, contact support.</p>
        <Button className="mt-4" onClick={() => window.location.reload()}>Reload page</Button>
      </div>
    )
  }
}
