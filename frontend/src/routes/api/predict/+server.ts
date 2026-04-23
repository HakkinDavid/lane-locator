import { json } from '@sveltejs/kit';

import type { RequestHandler } from './$types';

function normalizarUrl(url: string) {
	const limpia = url.trim();
	if (!limpia) {
		throw new Error('Ingresa la URL del backend.');
	}

	const destino = new URL(limpia);
	if (!['http:', 'https:'].includes(destino.protocol)) {
		throw new Error('La URL del backend debe usar http o https.');
	}

	return destino.toString();
}

export const POST: RequestHandler = async ({ request, fetch }) => {
	try {
		const datos = await request.formData();
		const archivo = datos.get('file');
		const url = datos.get('targetUrl');

		if (!(archivo instanceof File)) {
			return json({ error: 'No se recibió ningún archivo.' }, { status: 400 });
		}

		if (typeof url !== 'string') {
			return json({ error: 'No se recibió la URL del backend.' }, { status: 400 });
		}

		const envio = new FormData();
		envio.append('file', archivo, archivo.name);

		const respuesta = await fetch(normalizarUrl(url), {
			method: 'POST',
			body: envio
		});

		const tipo = respuesta.headers.get('content-type') ?? '';
		const cuerpo = tipo.includes('application/json')
			? await respuesta.json()
			: { error: await respuesta.text() };

		return json(cuerpo, { status: respuesta.status });
	} catch (e) {
		return json(
			{
				error: e instanceof Error ? e.message : 'No fue posible contactar con el backend.'
			},
			{ status: 502 }
		);
	}
};
