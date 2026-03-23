import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-navy-900 flex items-center justify-center p-8">
          <div className="max-w-md w-full text-center">
            <h1 className="text-2xl font-heading font-bold text-gray-100 mb-3">
              Something went wrong
            </h1>
            <p className="text-sm font-body text-gray-400 mb-6">
              An unexpected error occurred. Try reloading the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 bg-cyan/10 text-cyan border border-cyan/20 rounded-xl text-sm font-body font-medium hover:bg-cyan/20 transition-colors"
            >
              Reload
            </button>
            {this.state.error && (
              <details className="mt-6 text-left">
                <summary className="text-xs font-body text-gray-600 cursor-pointer hover:text-gray-400 transition-colors">
                  Error details
                </summary>
                <pre className="mt-2 p-3 bg-white/[0.03] border border-white/[0.06] rounded-lg text-xs font-body text-gray-500 overflow-auto max-h-40">
                  {this.state.error.message}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
