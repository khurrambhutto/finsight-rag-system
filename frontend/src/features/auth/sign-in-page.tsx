import { SignIn } from "@clerk/react";

export function SignInPage() {
  return (
    <div className="auth-page">
      <div className="auth-brand">
        <div className="auth-brand-icon">R</div>
        <p className="auth-brand-name">RAG System</p>
        <p className="auth-brand-sub">Sign in to continue</p>
      </div>

      <SignIn
        path="/sign-in"
        routing="path"
        fallbackRedirectUrl="/app/chat"
        signUpFallbackRedirectUrl="/app/chat"
        appearance={{
          variables: {
            colorBackground: "#111114",
            colorInputBackground: "#18181c",
            colorInputText: "#f4f4f5",
            colorText: "#f4f4f5",
            colorPrimary: "#818cf8",
            colorTextSecondary: "#a1a1aa",
            colorNeutral: "#18181c",
            colorDanger: "#fca5a5",
            borderRadius: "10px",
            fontFamily: "Inter, -apple-system, sans-serif",
            fontSize: "15px",
          },
          elements: {
            card: {
              boxShadow: "0 0 0 1px rgba(255,255,255,0.06)",
              background: "#111114",
            },
            headerTitle: {
              fontSize: "17px",
              fontWeight: "600",
              letterSpacing: "-0.01em",
            },
            headerSubtitle: {
              color: "#a1a1aa",
            },
            dividerLine: {
              background: "rgba(255,255,255,0.06)",
            },
            dividerText: {
              color: "#52525b",
            },
            formFieldLabel: {
              color: "#a1a1aa",
              fontSize: "13px",
              fontWeight: "500",
            },
            formFieldInput: {
              border: "1px solid rgba(255,255,255,0.08)",
              background: "#18181c",
              color: "#f4f4f5",
              fontSize: "14px",
            },
            formButtonPrimary: {
              background: "#818cf8",
              fontSize: "14px",
              fontWeight: "500",
            },
            footerActionLink: {
              color: "#818cf8",
            },
            identityPreviewText: {
              color: "#a1a1aa",
            },
            socialButtonsBlockButton: {
              border: "1px solid rgba(255,255,255,0.08)",
              background: "#18181c",
              color: "#f4f4f5",
            },
            socialButtonsBlockButtonText: {
              color: "#f4f4f5",
              fontWeight: "500",
            },
          },
        }}
      />
    </div>
  );
}
