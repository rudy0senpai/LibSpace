import { Component } from 'react';

export default class RenderErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    if (import.meta.env.DEV) {
      console.error('LibSphere page render failed', error, info.componentStack);
    }
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="auth-error-screen" role="alert">
          <h1>This page could not be displayed</h1>
          <p>Your session and catalogue data are unchanged. Reload to try again.</p>
          <button type="button" onClick={() => window.location.reload()}>Reload page</button>
        </main>
      );
    }
    return this.props.children;
  }
}
