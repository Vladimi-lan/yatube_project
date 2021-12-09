from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from http import HTTPStatus

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        # Делаем запрос к главной странице и проверяем статус
        response = self.guest_client.get('/')
        # Утверждаем, что для прохождения теста код должен быть равен 200
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorpage(self):
        """ Тестируем страницу об авторе """
        response = self.guest_client.get('/about/author/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_techpage(self):
        """ Тестируем страницу технологии """
        response = self.guest_client.get('/about/tech/')
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostUrlsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(
            username='Author'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            pub_date='20.11.2021',

        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.user = User.objects.create_user(username='NonAuthor')
        self.authorized_client.force_login(self.user)
        self.authorized_client_author.force_login(self.author)

    def test_urls_exists_at_desired_location_guest(self):
        """Тестируем доступность страниц для не авторизованного пользователя"""
        templates_url_names = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/Author/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/posts/1/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            'unexisting_page/': HTTPStatus.NOT_FOUND,
            '/follow/': HTTPStatus.FOUND,
        }
        for adress, code in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, code)

    def test_urls_exists_at_desired_location_authorized(self):
        """
        Тестируем доступность страниц
        для авторизованного пользователя не автора
        """
        templates_url_names = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/NonAuthor/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/posts/1/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            'unexisting_page/': HTTPStatus.NOT_FOUND,
            '/follow/': HTTPStatus.OK,
        }
        for adress, code in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, code)

    def test_urls_exists_at_desired_location_authorized_author(self):
        """
        Тестируем доступность страницы редактирования
        для авторизованного пользователя автора
        """
        response = self.authorized_client_author.get('/posts/1/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/Author/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client_author.get(adress)
                self.assertTemplateUsed(response, template)
