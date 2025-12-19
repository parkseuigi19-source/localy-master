import { AnimatePresence } from 'motion/react';
import { useState } from 'react';
import { LoginForm } from './LoginForm';
import { SignupForm } from './SignUpForm';
import { TermsAgreementForm } from './TermsAgreementForm';

interface AuthPageProps {
    onBack: () => void;
    onLoginSuccess: () => void;
    onSignupSuccess: (name: string) => void;
    initialMode?: 'login' | 'terms';
}

export function AuthPage({ onBack, onLoginSuccess, onSignupSuccess, initialMode = 'login' }: AuthPageProps) {
    const [mode, setMode] = useState<'login' | 'terms' | 'signup'>(initialMode);

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(135deg, rgba(45, 139, 95, 0.1) 0%, rgba(59, 164, 116, 0.1) 100%)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            overflowY: 'auto'
        }}>
            {/* 로그인/약관/회원가입 폼 */}
            <AnimatePresence mode="wait">
                {mode === 'login' ? (
                    <LoginForm
                        key="login"
                        onSwitchToSignup={() => setMode('terms')}
                        onLoginSuccess={onLoginSuccess}
                        onBack={onBack}
                    />
                ) : mode === 'terms' ? (
                    <TermsAgreementForm
                        key="terms"
                        onNext={() => setMode('signup')}
                        onBack={onBack}
                    />
                ) : (
                    <SignupForm
                        key="signup"
                        onSwitchToLogin={() => setMode('login')}
                        onBack={() => setMode('terms')}
                        onSignupSuccess={onSignupSuccess}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}
