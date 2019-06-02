reen.ios.ios_capture_utils import *

def get_poco_json():
    if provider.manager_current_dict.get('capturing'):
        device_size = get_device_size()
        session = provider.manager_current_dict.get('session')
        # if none or empty, use default addr
        address_string = provider.get_device_address()
        # fit wda format, make url start with http://
        if not address_string.startswith("http://"):
            address_string = "http://" + address_string

        url = address_string + "source?format=json"
        reqs = session.get(url=url)
        json_str = json.loads(reqs.text)
        dump_json = ios_dump_json(json_str['value'], device_size)
        provider.manager_current_dict['poco'] = dump_json


class IOSBridge(object):

    def __init__(self):
        self.select_element_paths = []
        self.json_str = ''
        # 开启持久连接  减少tcp连接的创建和销毁，提升服务器的处理性能
        self.session = requests.Session()
        self.timer = None

    @staticmethod
    def device_ui_json():
        poco_json = provider.manager_current_dict.get('poco')
        if poco_json is None:
            get_poco_json()
        return provider.manager_current_dict.get('poco')

    # 获取该位置下 最合适的UI元素的信息
    def get_select_element_dictionary(self, pos):
        # 重置
        self.select_element_paths = []
        poco_json = self.device_ui_json()
        if poco_json is None:
            return
        self.list_dictionary(dictionary=poco_json, pos=pos)
        list_sort = sorted(self.select_element_paths, key=lambda e: e.__getitem__('payload').__getitem__('size'))
        # 1.按照size排序
        min_size_dictionary = list_sort[0]
        element_dictionary = min_size_dictionary
        # 2.按照name排序 other 排后面
        for dictionary in list_sort:
            if dictionary['name'] == 'Other':
                list_sort.remove(dictionary)
        # 3.如果size相同 取name不是other的元素
        if len(list_sort) > 0:
            not_other_name_dictionary = list_sort[0]
            if not_other_name_dictionary['payload']['size'] == min_size_dictionary['payload']['size']:
                element_dictionary = not_other_name_dictionary

        return element_dictionary

    def get_element(self, pos):
        poco_json = self.device_ui_json()
        element_dictionary = self.get_select_element_dictionary(pos=pos)
        element_actiom = ElementAction(element_dictionary=element_dictionary, device_source=poco_json)
        return element_actiom

    def list_dictionary(self, dictionary, pos, parent_dic=None):

        if "payload" in dictionary:
            pos_x, pos_y = pos
            # 在该控件范围内，则继续向下遍历
            child_path_can_find = False
            if "children" in dictionary:
                for child in dictionary["children"]:
                    child_size_w, child_size_h = child["payload"]["size"]
                    child_pos_x, child_pos_y = child["payload"]["pos"]
                    if (pos_x >= child_pos_x - child_size_w/2) and (pos_x <= child_pos_x + child_size_w/2) \
                            and (pos_y >= child_pos_y - child_size_h/2) and (pos_y <= child_pos_y + child_size_h/2):
                        child_path_can_find = True
                        self.list_dictionary(dictionary=child, pos=pos, parent_dic=dictionary)
                # 如果该元素的子元素均不满足条件则返回该元素
                if child_path_can_find is False:
                    # 排除元素是Other的情况 Other不可交互
                    if dictionary.get('name') != 'Other':
                        self.select_element_paths.append(dictionary)
                    else:
                        self.select_element_paths.append(parent_dic)

            elif dictionary.get('name') != 'Other':
                self.select_element_paths.append(dictionary)
            else:
                self.select_element_paths.append(parent_dic)

    # 开启多线程获取ui控件树信息
    def start_get_data(self):
        provider.manager_current_dict['session'] = self.session
        try:
            provider.get_pool().apply_async(func=get_poco_json, args=())
        except ValueError as e:
            provider.logger.error(e)

        self.timer = threading.Timer(5, self.start_get_data)
        self.timer.start()

    def stop_get_device_ui_json(self):
            self.session.close()
            self.timer.cancel()






