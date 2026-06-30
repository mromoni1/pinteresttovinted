export default function PrivacyPage() {
  return (
    <main className="max-w-2xl mx-auto px-8 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Privacy Policy</h1>
      <p className="mt-2 text-sm text-gray-400">Last updated: June 2025</p>

      <section className="mt-10 space-y-6 text-gray-700 leading-relaxed">
        <div>
          <h2 className="font-semibold text-gray-900 mb-1">What StyleMatch is</h2>
          <p>
            StyleMatch is a personal styling tool that reads your Pinterest boards,
            extracts your aesthetic, and surfaces matching secondhand listings on
            Vinted. It is a single-user personal tool, not a commercial product.
          </p>
        </div>

        <div>
          <h2 className="font-semibold text-gray-900 mb-1">Data collected</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>
              <span className="font-medium">Google account:</span> your email address
              and Google ID, used only to identify your session.
            </li>
            <li>
              <span className="font-medium">Pinterest boards and pins:</span> board
              names, pin images, and metadata — read-only, used to generate style
              recommendations.
            </li>
            <li>
              <span className="font-medium">Style preferences:</span> size, price
              range, and style keywords you enter in the app.
            </li>
          </ul>
        </div>

        <div>
          <h2 className="font-semibold text-gray-900 mb-1">How data is stored</h2>
          <p>
            Your Google session and style preferences are stored in Supabase (a
            hosted Postgres database). Your Pinterest OAuth token is stored locally
            on the device running the app and is never sent to any server.
          </p>
        </div>

        <div>
          <h2 className="font-semibold text-gray-900 mb-1">Data sharing</h2>
          <p>
            Your data is not sold, rented, or shared with any third party. It is
            used solely to operate the app for your personal use.
          </p>
        </div>

        <div>
          <h2 className="font-semibold text-gray-900 mb-1">Third-party services</h2>
          <p>
            StyleMatch connects to Pinterest (to read your boards and pins) and
            Vinted (to search secondhand listings). Your interactions with those
            services are governed by their own privacy policies.
          </p>
        </div>

        <div>
          <h2 className="font-semibold text-gray-900 mb-1">Contact</h2>
          <p>
            Questions? Reach out at{" "}
            <a
              href="mailto:mariaromonichols@gmail.com"
              className="underline hover:text-black transition-colors"
            >
              mariaromonichols@gmail.com
            </a>
            .
          </p>
        </div>
      </section>
    </main>
  );
}
