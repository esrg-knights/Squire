.PHONY: dev test start-cache

dev:
	python manage.py runserver --settings squire.settings_local

TARGET ?=
test: ## Run tests (TARGET=Path to a module, folder, file, class, or method to test)
	-coverage run manage.py test $(TARGET)
	coverage html

start-cache:
	memcached -m 64 -p 11211 -u memcache
