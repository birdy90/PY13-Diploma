import json
import math
import sys
import requests


class VKErrors:
    TOO_MANY_REQUESTS = 6
    NOT_ENOUGH_RIGHTS = 7
    ACCESS_DENIED = 15
    USER_DELETED = 18


class VK:
    API_URL_BASE = 'https://api.vk.com/method/'
    TOKEN = 'from config.json'
    API_VERSION = '5.74'

    def __init__(self, token):
        self.TOKEN = token

    def request(self, method, data):

        if not isinstance(data, dict):
            print('Trying to send some false data. You need dictionary')
            return []

        data['access_token'] = self.TOKEN
        data['v'] = self.API_VERSION

        request_url = '{0}{1}'.format(self.API_URL_BASE, method)

        while True:
            try:
                response = requests.get(request_url, params=data)
            except requests.ReadTimeout:
                print('The server did not send any data in the allotted amount of time. Trying one more time')
                continue

            json_response = response.json()

            if 'error' in json_response:
                if json_response['error']['error_code'] == VKErrors.TOO_MANY_REQUESTS:
                    continue
                elif json_response['error']['error_code'] in \
                        (
                            VKErrors.ACCESS_DENIED,
                            VKErrors.NOT_ENOUGH_RIGHTS,
                            VKErrors.USER_DELETED
                        ):
                    return []
                else:
                    print('Some undefined error. Check if your token is right')
                    return []

            break

        return json_response['response']

    def user_groups(self, uid):
        return self.request('groups.get', {
            'user_id': uid,
            'count': 1000
        })

    def user_friends(self, uid):
        chunk_offset = 0
        chunk_size = 2500
        friends = {}
        while True:
            data_chunk = self.request('friends.get', {
                'user_id': uid,
                'offset': chunk_offset,
                'count': chunk_size
            })
            chunk_offset += chunk_size

            if len(friends) == 0:
                friends = data_chunk
            else:
                friends['items'] = friends['items'] + data_chunk['items']

            if chunk_offset > data_chunk['count']:
                break
        return friends

    def user_subscribers(self, uid):
        chunk_offset = 0
        chunk_size = 100
        friends = []
        while True:
            data_chunk = self.request('users.getFollowers', {
                'user_id': uid,
                'offset': chunk_offset,
                'count': chunk_size
            })
            chunk_offset += chunk_size

            if len(friends) == 0:
                friends = data_chunk
            else:
                friends['items'] = friends['items'] + data_chunk['items']

            if len(data_chunk['items']) < chunk_size:
                break
        return friends

    def user_friends_and_subscribers(self, uid):
        friends = self.user_friends(uid)
        subscribers = self.user_subscribers(uid)
        friends['count'] = friends['count'] + subscribers['count']
        friends['items'] = friends['items'] + subscribers['items']
        return friends


def progress_counter(current, overall):
    number_of_bins = 20
    bin_size = overall / number_of_bins

    hashes_number = int(current // bin_size)
    dots_number = int((overall - current) // bin_size)
    percentage = str(math.floor(10000 * current / overall) / 100) + '%'

    print('[' + '#' * hashes_number + '.' * dots_number + '] ' + percentage)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


def get_settings():
    with open('./config.json', 'r') as file:
        return json.load(file)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('You haven\'t assigned username/userid. Try to add it')
        exit(0)

    settings = get_settings()

    user_id = sys.argv[1]

    print('Started')

    vk = VK('sasd')

    print('Retrieving current user groups')
    users = vk.request('users.get', {'user_ids': user_id})

    if len(users) == 0:
        print('There is no users with such credentials: {}'.format(user_id))
        exit(0)

    if len(users) > 1:
        print('It\'s strange, but you found more than one user')
        exit(0)

    current_user = users[0]
    current_user_groups = vk.user_groups(current_user['id'])
    print('{} found'.format(current_user_groups['count']))

    print('Getting user friends')
    current_user_friends = vk.user_friends_and_subscribers(current_user['id'])
    print('Found {} friends'.format(current_user_friends['count']))

    print('Checking friend\'s groups')
    overall_items = current_user_friends['count']
    current_user_groups = set(current_user_groups['items'])

    for current_index, friend_id in enumerate(current_user_friends['items']):
        friend_groups = vk.user_groups(friend_id)
        if len(friend_groups) == 0:
            continue
        current_user_groups = current_user_groups.difference(set(friend_groups['items']))
        progress_counter(current_index, overall_items)
    print('{} found'.format(len(current_user_groups)))

    current_user_groups = list(current_user_groups)
    groups_data = []
    for chunk in chunks(current_user_groups, 250):
        groups_data += vk.request('groups.getById', {
            'group_ids': ','.join([str(g) for g in chunk]),
            'fields': 'members_count'
        })

    groups_data_filtered = [
        {
            'name': item['name'],
            'gid': item['id'],
            'members_count': item['members_count'] if 'members_count' in item else -1
        }
        for item in groups_data
    ]

    groups_data_filtered = {
        'count': len(groups_data_filtered),
        'items': groups_data_filtered
    }

    with open('groups.json', 'w', encoding='utf-8') as f:
        json.dump(groups_data_filtered, f, indent=2, ensure_ascii=False)

    print('Finished. See the \'./groups.json\' file')
