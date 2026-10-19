import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import '../src/index.css'
import Modal from '../src/components/ui/Modal'
import DateTimePicker from '../src/components/ui/DateTimePicker'

export function Harness() {
  const [start, setStart] = useState<Date | null>(null)
  const [end, setEnd] = useState<Date | null>(null)
  return <main className="min-h-screen bg-void p-4">
    <Modal open onClose={() => {}} title="New event" className="max-w-md">
      <div className="flex flex-col gap-4">
        <label className="text-sm text-text-muted">Title<input className="w-full p-3" value="Calendar test" readOnly /></label>
        <DateTimePicker label="Starts" value={start} onChange={setStart} />
        <DateTimePicker label="Ends" value={end} onChange={setEnd} minDate={start ?? undefined} />
        <button type="button" className="p-3 text-text-primary">Create event</button>
      </div>
    </Modal>
  </main>
}

createRoot(document.getElementById('root')!).render(<Harness />)
