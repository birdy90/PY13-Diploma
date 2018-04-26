import json
import math
import sys
import requests


class VK:
    API_URL_BASE = 'https://api.vk.com/method/'
    TOKEN = '7b23e40ad10e08d3b7a8ec0956f2c57910c455e886b480b7d9fb59859870658c4a0b8fdc4dd494db19099'
    API_VERSION = '5.74'

    def request(self, method, data):

        if type(data) is not dict:
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

            # checking for errors
            if 'error' in json_response:
                if json_response['error']['error_code'] == 6:  # too many requests
                    continue
                elif json_response['error']['error_code'] == 15:  # access denied
                    print('Access denied to {}')
                    return []
                elif json_response['error']['error_code'] == 7:  # not enough rights
                    return []
                elif json_response['error']['error_code'] == 18:  # user was deleted
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
        friends = []
        while True:
            chunk = self.request('friends.get', {
                'user_id': uid,
                'offset': chunk_offset,
                'count': chunk_size
            })
            chunk_offset += chunk_size

            if len(friends) == 0:
                friends = chunk
            else:
                friends['items'] = friends['items'] + chunk['items']

            if len(chunk['items']) < chunk_size:
                break
        return friends

    def user_subscribers(self, uid):
        chunk_offset = 0
        chunk_size = 100
        friends = []
        while True:
            chunk = self.request('users.getFollowers', {
                'user_id': uid,
                'offset': chunk_offset,
                'count': chunk_size
            })
            chunk_offset += chunk_size

            if len(friends) == 0:
                friends = chunk
            else:
                friends['items'] = friends['items'] + chunk['items']

            if len(chunk['items']) < chunk_size:
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
    percentage = str(math.floor(10000 * current / overall) / 100) + '%'
    print('[' + '#' * int(current / bin_size) + '.' * int(math.ceil((overall - current) / bin_size)) + '] ' + percentage, end='\r\n')


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('You haven\'t assigned username/userid. Try to add it')
        exit(0)

    user_id = sys.argv[1]

    print('Started')

    vk = VK()

    print('Retrieving current user groups')
    current_user = vk.request('users.get', {'user_ids': user_id})[0]
    current_user_groups = vk.user_groups(current_user['id'])
    print('{} found'.format(current_user_groups['count']))

    print('Getting user friends')
    current_user_friends = vk.user_friends_and_subscribers(current_user['id'])
    print('Found {} friends'.format(current_user_friends['count']))

    print('Checking friend\'s groups')
    current_index = 0
    overall_items = current_user_friends['count']
    current_user_groups = set(current_user_groups['items'])

    for friend_id in current_user_friends['items']:
        friend_groups = vk.user_groups(friend_id)
        if len(friend_groups) == 0:
            continue
        current_user_groups = current_user_groups.difference(set(friend_groups['items']))
        current_index += 1
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
