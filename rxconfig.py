import reflex as rx

config = rx.Config(
	app_name="pdf_signature",
	plugins=[rx.plugins.TailwindV3Plugin()],
	disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
