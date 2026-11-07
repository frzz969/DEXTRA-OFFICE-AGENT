import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.DEXTRA_API_URL ?? 'http://127.0.0.1:8000';

async function proxy(req: NextRequest, { params }: { params: Promise<{ proxy: string[] }> }) {
  const { proxy: segments } = await params;
  const path = segments.join('/');
  const url = new URL(`/api/${path}`, BACKEND);
  req.nextUrl.searchParams.forEach((v, k) => url.searchParams.set(k, v));
  const init: RequestInit = { method: req.method, headers: {} };
  const ct = req.headers.get('content-type');
  if (ct) (init.headers as Record<string, string>)['content-type'] = ct;
  const csrf = req.headers.get('x-csrf-token');
  if (csrf) (init.headers as Record<string, string>)['x-csrf-token'] = csrf;
  const cookie = req.headers.get('cookie');
  if (cookie) (init.headers as Record<string, string>)['cookie'] = cookie;
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = await req.text();
  }
  const res = await fetch(url.toString(), init);
  const body = await res.arrayBuffer();
  const out = new NextResponse(body, { status: res.status });
  res.headers.forEach((v, k) => {
    if (k.toLowerCase() !== 'transfer-encoding' && k.toLowerCase() !== 'content-encoding') out.headers.set(k, v);
  });
  return out;
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };