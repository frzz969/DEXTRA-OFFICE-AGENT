'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import type { LoginResponseDto } from '@/lib/api-types';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [pendingMfa, setPendingMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.post<LoginResponseDto>('/api/v1/auth/login', {
        email,
        password,
        mfa_code: pendingMfa ? mfaCode : undefined,
      });
      if (res.mfa_required) {
        setPendingMfa(true);
        setLoading(false);
        return;
      }
      router.push('/overview');
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login gagal.');
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC]">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 rounded-lg bg-white p-6 shadow">
        <h1 className="text-xl font-semibold">Masuk</h1>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <input
          className="w-full rounded border px-3 py-2"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="w-full rounded border px-3 py-2"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {pendingMfa && (
          <input
            className="w-full rounded border px-3 py-2"
            placeholder="Kode MFA"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
          />
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 py-2 text-white disabled:opacity-50"
        >
          {loading ? 'Memproses...' : 'Masuk'}
        </button>
      </form>
    </div>
  );
}
