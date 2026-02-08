import Link from "next/link";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-6">
              <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Admin
              </h1>
              <nav className="flex items-center gap-4">
                <Link
                  href="/admin/embeddings"
                  className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                >
                  Embeddings
                </Link>
                <Link
                  href="/admin/training-data"
                  className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                >
                  Training Data
                </Link>
              </nav>
            </div>
            <Link
              href="/chat"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              Back to Chat
            </Link>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
