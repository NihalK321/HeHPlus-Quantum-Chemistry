import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

export function NotFoundPage() {
  return (
    <section className="research-panel mx-auto max-w-xl p-8 text-center">
      <span className="mx-auto grid h-11 w-11 place-items-center rounded-lg bg-teal-50 text-teal-700"><Compass className="h-5 w-5" aria-hidden="true" /></span>
      <p className="research-eyebrow mt-5">Route unavailable</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-[#172B3A]">This workspace route does not exist.</h1>
      <p className="mt-3 text-sm leading-6 text-[#657B85]">Return to the research dashboard to continue exploring the PepperQ prototype.</p>
      <Link
        className="mt-6 inline-flex rounded-lg border border-teal-700 bg-teal-700 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-teal-800"
        to="/"
      >
        Go to dashboard
      </Link>
    </section>
  )
}
