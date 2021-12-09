import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from http import HTTPStatus

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(
            username='Author'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
            image=cls.uploaded
        )
        cls.pub_date = cls.post.pub_date

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='Zuev')
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_author.force_login(self.author)

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': (
                reverse('posts:group_list', kwargs={'slug': self.group.slug})
            ),
            'posts/profile.html': (
                reverse(
                    'posts:profile',
                    kwargs={'username': self.author.username}
                )
            ),
            'posts/post_detail.html': (
                reverse('posts:post_detail', kwargs={'post_id': self.post.id})
            ),
            'posts/create_post.html': reverse('posts:post_create'),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_pages_use_correct_template_author(self):
        """
        URL-адрес страницы редактирования поста использует
        соответствующий шаблон.
        """
        template = 'posts/create_post.html'
        reverse_name = (
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        response = self.authorized_client_author.get(reverse_name)
        self.assertTemplateUsed(response, template)

    def test_all_page_show_correct_context(self):
        """
        Шаблон index, group_list, profile
        сформирован с правильным контекстом.
        """
        post_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author.username})
        ]
        for page in post_pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(
                    (response.context['page_obj'][0]), self.post)

    def test_posts_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'].title, self.group.title)

    def test_posts_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(response.context['post_count'], 1)
        self.assertEqual(
            response.context['author'].username,
            self.author.username
        )

    def test_posts_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context['post_count'], 1)
        self.assertEqual(
            response.context['author'].username,
            self.author.username
        )

    def test_create_post_new_show_correct_context(self):
        """
        Шаблон create_post для создания поста сформирован
        с правильным контекстом.
        """
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_edit_show_correct_context(self):
        """
        Шаблон create_post для редактирования поста сформирован
        с правильным контекстом.
        """
        response = self.authorized_client_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(
            response.context.get('form').instance.text, self.post.text
        )
        self.assertEqual(
            response.context.get('form').instance.group.title,
            self.post.group.title
        )

    def test_pages_context_has_image(self):
        """
        При выводе поста с картинкой в index, group_list, profile
        изображение передаётся в словаре.
        """
        post_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            )
        ]
        for page in post_pages:
            with self.subTest(page=page):
                response = self.guest_client.get(page)
                self.assertEqual(
                    (response.context['page_obj'][0].image),
                    self.post.image
                )

    def test_post_detail_page_context_has_image(self):
        """
        При выводе поста с картинкой в post_detail
        изображение передаётся в словаре.
        """
        response = self.guest_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(
            (response.context['post'].image),
            self.post.image
        )

    def test_cache_on_index_page(self):
        """ При удалении записи из базы, пост будет доступен из кэш."""
        cache.clear()
        post = Post.objects.create(
            author=self.author,
            text='Текст поста'
        )
        response = self.guest_client.get(
            reverse('posts:index')
        )
        post.delete()
        self.assertIn(post.text, response.content.decode())
        cache.clear()
        response = self.guest_client.get(
            reverse('posts:index')
        )
        self.assertNotIn(post.text, response.content.decode())

    def test_follow(self):
        """
        Авторизованный пользователь
        может подписываться на других пользователей.
        """
        followings = Follow.objects.filter(
            user=self.user, author=self.author
        ).count()
        response = self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author},
            ),
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            Follow.objects.filter(user=self.user, author=self.author).count(),
            followings + 1
        )
        self.assertEqual(
            Follow.objects.filter(user=self.user, author=self.author).exists(),
            True
        )

    def test_unfollow(self):
        """Авторизованный пользователь может отписываться."""
        self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author},
            ),
            follow=True
        )
        self.authorized_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author},
            ),
            follow=True
        )
        self.assertEqual(
            Follow.objects.filter(user=self.user, author=self.author).exists(),
            False
        )

    def test_follow_page_context_following(self):
        """
        Новая запись пользователя появляется в ленте тех,
        кто на него подписан.
        """
        Follow.objects.create(
            user=self.user, author=self.author
        )
        post = Post.objects.create(
            author=self.author,
            text='Текст поста'
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(post, response.context['page_obj'])

    def test_follow_page_context_not_following(self):
        """
        Новая запись пользователя НЕ появляется в ленте тех, кто не подписан.
        """
        post = Post.objects.create(
            author=self.author,
            text='Текст поста'
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(
            username='Author'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.posts = []
        for i in range(1, 14):
            cls.posts.append(Post(
                text=f'Тестовый текст {i}',
                author=cls.author,
                group=cls.group,
            ))
        Post.objects.bulk_create(cls.posts)
        cls.first_page_objs = 10
        cls.second_page_objs = 3

    def setUp(self):
        self.client = Client()

    def test_first_page_contains_ten_records(self):
        pages_names = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        for page in pages_names:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.first_page_objs
                )

    def test_second_page_contains_three_records(self):
        pages_names = (
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
            + '?page=2',
            reverse('posts:profile', kwargs={'username': self.author.username})
            + '?page=2',
        )
        for page in pages_names:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.second_page_objs
                )
