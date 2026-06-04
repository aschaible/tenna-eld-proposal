import { next } from '@vercel/functions';

export default function middleware(request: Request) {
  const auth = request.headers.get('authorization');

  if (auth?.startsWith('Basic ')) {
    const [user, pass] = atob(auth.slice(6)).split(':');
    if (
      user === process.env.BASIC_AUTH_USER &&
      pass === process.env.BASIC_AUTH_PASSWORD
    ) {
      return next();
    }
  }

  return new Response('Authentication required', {
    status: 401,
    headers: { 'WWW-Authenticate': 'Basic realm="AppAxis", charset="UTF-8"' },
  });
}

export const config = {
  matcher: '/(.*)',
};
